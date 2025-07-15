import os, time, requests
import requests, io
from celery import shared_task
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from user.models import User
from product.models import Product
from fitting.models import FittingResult
from fitting.utils import upload_fitting_image_to_s3


BITSTUDIO_API_KEY = os.environ["BITSTUDIO_API_KEY"]

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def run_vto_task(self, person_id, outfit_id, prompt):
    """단일 프롬프트용 VTO 실행 → path 또는 None"""
    try:
        # ① 작업 시작
        res = requests.post(
            "https://api.bitstudio.ai/images/virtual-try-on",
            headers={"Authorization": f"Bearer {BITSTUDIO_API_KEY}",
                     "Content-Type": "application/json"},
            json={
                "person_image_id": person_id,
                "outfit_image_id": outfit_id,
                "prompt": prompt,
                "resolution": "standard",
                "num_images": 1,
                "style": "studio",
            },
            timeout=30,
        )
        res.raise_for_status()
        job_id = res.json()[0]["id"]

        # ② 완료 폴링
        for _ in range(15):
            info = requests.get(
                f"https://api.bitstudio.ai/images/{job_id}",
                headers={"Authorization": f"Bearer {BITSTUDIO_API_KEY}"},
                timeout=10,
            ).json()

            if info.get("status") == "completed":
                return info.get("path")
            if info.get("status") == "failed":
                return None
            time.sleep(2)

        return None  # 타임아웃
    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task
def collect_paths(results):
    """
    chord callback.
    results: [path1, path2, path3, path4]
    그대로 반환하거나 후처리(저장·DB업데이트 등) 가능
    """
    return results  # 필요하면 JSON 직렬화 등 추가

# fitting/tasks.py  (추가 부분만)
@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def run_vto_url_task(self, person_url, outfit_url, prompt):
    """
    Bitstudio에 URL만 넘겨 VTO 1장을 생성 → 완료 path | None
    """
    try:
        # ① 작업 시작
        r = requests.post(
            "https://api.bitstudio.ai/images/virtual-try-on",
            headers={"Authorization": f"Bearer {BITSTUDIO_API_KEY}",
                     "Content-Type": "application/json"},
            json={
                "person_image_url":  person_url,
                "outfit_image_url":  outfit_url,
                "prompt":            prompt,
                "resolution":        "standard",
                "num_images":        1,
                "style":             "studio",
            },
            timeout=60,
        )
        r.raise_for_status()
        job_id = r.json()[0]["id"]

        # ② 완료 폴링 (2 초 × 30 = 60 초)
        for _ in range(30):
            info = requests.get(
                f"https://api.bitstudio.ai/images/{job_id}",
                headers={"Authorization": f"Bearer {BITSTUDIO_API_KEY}"},
                timeout=10,
            ).json()

            if info.get("status") == "completed":
                return info.get("path")
            if info.get("status") == "failed":
                return None
            time.sleep(2)

        return None            # 타임아웃
    except Exception as exc:
        raise self.retry(exc=exc)
    
@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def save_to_s3_and_db(self, vto_url: str, user_id: int, product_id: int):
    if not vto_url:
        return None   # 이전 태스크 실패한 경우

    try:
        # 1) 이미지 다운로드
        resp = requests.get(vto_url, timeout=30)
        resp.raise_for_status()
        img_bytes = resp.content

        # 2) S3 업로드
        s3_url = upload_fitting_image_to_s3(
            user_id=user_id,
            product_id=product_id,
            image_data=img_bytes
        )

        # 3) DB 저장 (상품 1:1)
        user = User.objects.get(id=user_id)
        product = Product.objects.get(id=product_id)

        FittingResult.objects.update_or_create(
            product=product,                # 1:1 관계 기준
            defaults={
                "user":  user,
                "image": s3_url
            }
        )
        return s3_url

    except (requests.RequestException, ObjectDoesNotExist) as exc:
        # 네트워크 오류나 객체 미존재 시 재시도
        raise self.retry(exc=exc)
