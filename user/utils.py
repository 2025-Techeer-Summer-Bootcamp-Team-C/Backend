import os, io, uuid, boto3
from PIL import Image

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_S3_REGION_NAME"),
)

BUCKET = os.getenv("AWS_STORAGE_BUCKET_NAME")
CLOUDFRONT_DOMAIN = os.getenv("AWS_S3_CUSTOM_DOMAIN")

def resize_image_keep_ratio(image_bytes, max_size=(800, 800), quality=90):
    """
    원본 비율을 유지하여 긴 변이 max_size 이하가 되도록 리사이즈
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert("RGB")
        img.thumbnail(max_size, Image.LANCZOS)  # 비율 유지 자동
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        return buffer.getvalue()

def upload_profile_image_to_s3(user_id: str, image_bytes: bytes, ext: str = "jpg") -> str:
    # 리사이즈 적용
    resized_bytes = resize_image_keep_ratio(image_bytes, max_size=(800, 800))
    key = f"profiles/{user_id}/{uuid.uuid4()}.{ext}"
    s3.upload_fileobj(
        io.BytesIO(resized_bytes),
        BUCKET,
        key,
        ExtraArgs={
            "ContentType": f"image/{ext}",
            "ContentDisposition": "inline",
        },
    )
    return f"{CLOUDFRONT_DOMAIN}/{key}"
