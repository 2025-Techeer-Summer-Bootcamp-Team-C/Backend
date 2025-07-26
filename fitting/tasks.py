import os, time, requests, uuid, random
import requests, io
from celery import shared_task
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from user.models import User, UserImage
from product.models import Product
from fitting.models import FittingResult
from fitting.utils import upload_fitting_image_to_s3, upload_video_to_s3
from celery import group, chain
from celery.exceptions import Ignore


BITSTUDIO_API_KEY = os.environ["BITSTUDIO_API_KEY"]

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
def save_to_s3_and_db(self, vto_url: str, user_image_id: int, product_id: int):
    if not vto_url:
        return None   # 이전 태스크 실패한 경우

    try:
        # 1) 이미지 다운로드
        resp = requests.get(vto_url, timeout=30)
        resp.raise_for_status()
        img_bytes = resp.content

        # 2) S3 업로드
        s3_url = upload_fitting_image_to_s3(
            user_image_id=user_image_id,
            product_id=product_id,
            image_data=img_bytes
        )

        # 3) DB 저장
        user_image = UserImage.objects.get(id=user_image_id)
        product = Product.objects.get(id=product_id)

        FittingResult.objects.update_or_create(
            user_image = user_image,
            product=product,                # 1:1 관계 기준
            defaults={
                "user_image":  user_image,
                "image": s3_url
            }
        )
        return s3_url

    except (requests.RequestException, ObjectDoesNotExist) as exc:
        # 네트워크 오류나 객체 미존재 시 재시도
        raise self.retry(exc=exc)
    
@shared_task(bind=True, max_retries=3, default_retry_delay=5, rate_limit='3/s')
def run_vto_edit_url_task(self, person_url, outfit_url, prompt):
    """
    Bitstudio에 URL만 넘겨 VTO 1장을 생성
    → 완료된 **이미지 ID** (job_id) 반환, 실패/타임아웃 시 None
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
        vto_image_id = r.json()[0]["id"]          # ← 결과 이미지 ID

        # ② 완료 폴링 (2초 × 30 = 60초)
        for _ in range(50):
            info = requests.get(
                f"https://api.bitstudio.ai/images/{vto_image_id}",
                headers={"Authorization": f"Bearer {BITSTUDIO_API_KEY}"},
                timeout=10,
            ).json()

            if info.get("status") == "completed" and info.get("path"):
                return vto_image_id              # ✅ 이미지 ID 반환
            if info.get("status") == "failed":
                raise self.retry(exc=RuntimeError("VTO status=failed"))
            time.sleep(2)

        return None  # 타임아웃
    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=2,
    rate_limit='3/s'
)
def edit_bg_task(self, vto_image_id):
    if not vto_image_id:
        # None 은 스킵
        raise Ignore("No VTO ID, skip edit_bg_task")
    # 1) Edit 요청
    r = requests.post(
        f"https://api.bitstudio.ai/images/{vto_image_id}/edit",
        headers={"Authorization": f"Bearer {BITSTUDIO_API_KEY}",
                 "Content-Type":  "application/json"},
        json={
            "prompt":      "Replace the background with a soft light-gray studio backdrop (#e8e8e8) and add a subtle floor shadow under the model for realism",
            "resolution":  "standard",
            "num_images":  1,
            "seed":        42
        },
        timeout=60,
    ).json()

    ver = r["versions"][0]
    result_id = ver.get("source_image_id") or ver["id"]
    poll_url  = (
        f"https://api.bitstudio.ai/images/{result_id}"
        if ver.get("source_image_id") else
        f"https://api.bitstudio.ai/images/versions/{result_id}"
    )

    # 2) 폴링 (5 s × 36 = 3분)
    for _ in range(36):
        info = requests.get(poll_url, headers={"Authorization": f"Bearer {BITSTUDIO_API_KEY}"}, timeout=15).json()
        if info["status"] == "completed" and info.get("path"):
            return info["path"]
        if info["status"] == "failed":
            return None
        time.sleep(5)
    return None

@shared_task
def generate_fitting_video_task(fitting_id, task_id):
    fitting = FittingResult.objects.get(pk=fitting_id)
    video_url = None

    # 최대 8분 5초마다 폴링
    for _ in range(48):
        time.sleep(10)
        resp = requests.post(
            "https://thenewblack.ai/api/1.1/wf/results_video",
            files={
                'email':    (None, os.getenv("TNB_EMAIL")),
                'password': (None, os.getenv("TNB_PASSWORD")),
                'id':       (None, task_id),
            }
        )
        if resp.status_code != 200:
            continue
        detail = resp.text.strip()
        if detail and detail.startswith("http"):
            video_url = detail
            break

    if not video_url:
        fitting.status = 'failed'
        fitting.save(update_fields=['status'])
        return

    # 비디오 다운로드
    video_resp = requests.get(video_url, stream=True)
    video_resp.raise_for_status()
    video_bytes = video_resp.content

    # S3 업로드 via utils.upload_bytes
    # prefix 에 사용자 이미지 id,상품 구분자 추가
    prefix = f"fitting_videos/{fitting.user_image.id}/{fitting.product.id}/"
    # ext="mp4" 로 지정
    s3_url = upload_video_to_s3(prefix, video_bytes, ext="mp4")

    # DB 업데이트
    fitting.video = s3_url
    fitting.status = 'completed'
    fitting.save(update_fields=['video', 'status'])
    
@shared_task(bind=True, max_retries=3, default_retry_delay=5, rate_limit='3/s', name="fitting.fake_run_vto")
def fake_run_vto(self, person_url, outfit_url, prompt):
    time.sleep(random.uniform(25, 35))  # 30초 근처
    # 10% 확률로 실패도 흉내
    if random.random() < 0.1:
        raise self.retry(exc=Exception("fake VTO error"))
    return f"fake-id-{uuid.uuid4()}"

@shared_task(bind=True, max_retries=3, default_retry_delay=5, rate_limit='3/s', name="fitting.fake_edit_bg")
def fake_edit_bg(self, vto_image_id):
    time.sleep(random.uniform(25, 35))
    if random.random() < 0.05:
        return None  # 실패 케이스
    return "https://placehold.co/1024x1536.png?text=FAKE_EDIT_BG"

@shared_task(bind=True, max_retries=2, default_retry_delay=10, name="fitting.fake_save_to_s3_and_db")
def fake_save_to_s3_and_db(self, vto_url: str, user_id: int, product_id: int):
    if not vto_url:
        return None
    # 실제 다운로드/업로드 없음. 바로 DB만 업데이트 등.
    from django.contrib.auth import get_user_model
    from product.models import Product
    from fitting.models import FittingResult

    User = get_user_model()
    user = User.objects.get(id=user_id)
    product = Product.objects.get(id=product_id)

    FittingResult.objects.update_or_create(
        user=user,
        product=product,
        defaults={"user": user, "image": vto_url}
    )
    return vto_url