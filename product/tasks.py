import io
from PIL import Image
from celery import shared_task

def resize_image_keep_ratio(image_bytes, max_size=(800, 800), quality=90):
    """(이미 있던 헬퍼 그대로 복사)"""
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert("RGB")
        img.thumbnail(max_size, Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality, optimize=True)
        return buf.getvalue()

@shared_task
def resize_one(image_bytes: bytes) -> int:
    """리사이즈 후 바이트 크기를 반환(테스트 용도)"""
    return len(resize_image_keep_ratio(image_bytes))