from celery import shared_task
import os, time, requests

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
            timeout=30,
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
