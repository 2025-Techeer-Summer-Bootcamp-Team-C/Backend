from PIL import Image
import io, os, uuid, boto3, mimetypes

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
    원본 비율 유지, 긴 변이 max_size 미만이 되도록 리사이즈 후 JPEG 저장 (용량 ↓)
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert("RGB")
        img.thumbnail(max_size, Image.LANCZOS)   # 비율 유지
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        return buffer.getvalue()

def compress_image_bytes(image_bytes, quality=90):
    """
    해상도 그대로, JPEG 재압축만 수행 (원본 크기 유지, 용량만 ↓)
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert("RGB")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        return buffer.getvalue()
    

def upload_video_to_s3(prefix: str, data: bytes, ext: str = "jpg") -> str:
    key = f"{prefix}{uuid.uuid4()}.{ext}"

    # 확장자 → MIME 타입 자동 매핑
    mime_type, _ = mimetypes.guess_type(f"file.{ext}")
    # 못 찾으면 기본값
    if mime_type is None:
        mime_type = "application/octet-stream"

    s3.upload_fileobj(
        io.BytesIO(data),
        BUCKET,
        key,
        ExtraArgs={
            "ContentType": mime_type,       # 예: video/mp4, image/jpeg
            "ContentDisposition": "inline", # 브라우저에서 바로 재생/표시
        },
    )
    return f"{CLOUDFRONT_DOMAIN}/{key}"

def upload_url(prefix: str, remote_url: str) -> str:
    resp = requests.get(remote_url, timeout=30)
    resp.raise_for_status()

    # 확장자 안전 추출
    filename = remote_url.split("/")[-1].split("?")[0]
    if "." in filename:
        ext = filename.split(".")[-1]
    else:
        ext = "jpg"

    return upload_bytes(prefix, resp.content, ext)

def upload_fitting_image_to_s3(
    user_id: int,
    product_id: int,
    image_data: bytes,
    variation: int | None = None,
    ext: str = "jpg",
) -> str:
    if variation is None:
        key = f"fitting_images/{user_id}/{product_id}/{uuid.uuid4()}.{ext}"
    else:
        key = f"fitting_images/{user_id}/{product_id}_{variation}_{uuid.uuid4()}.{ext}"

    s3.upload_fileobj(
        io.BytesIO(image_data),
        BUCKET,
        key,
        ExtraArgs={"ContentType": f"image/{ext}", "ContentDisposition": "inline"},
    )
    return f"{CLOUDFRONT_DOMAIN}/{key}"

def upload_fitting_image_to_s3(user_image_id, product_id, image_data, ext="jpg", resize=True):
    """
    리사이즈/재압축 후 S3 저장. resize=False면 해상도 그대로, True면 800x800 이하 비율 유
    """
    if resize:
        # 원본 비율 유지, 800px 이하로 리사이즈
        image_bytes = resize_image_keep_ratio(image_data, max_size=(800, 800))
    else:
        # 해상도 그대로, 재압축만
        image_bytes = compress_image_bytes(image_data)
    key = f"fitting_images/{user_image_id}/{product_id}/{uuid.uuid4()}.{ext}"
    s3.upload_fileobj(
        io.BytesIO(image_bytes),
        BUCKET,
        key,
        ExtraArgs={"ContentType": f"image/{ext}", "ContentDisposition": "inline"},
    )
    return f"{CLOUDFRONT_DOMAIN}/{key}"

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
