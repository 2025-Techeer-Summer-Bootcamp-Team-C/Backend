import os, io, uuid, boto3, requests

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_S3_REGION_NAME"),
)
BUCKET = os.getenv("AWS_STORAGE_BUCKET_NAME")
CLOUDFRONT_DOMAIN = os.getenv("AWS_S3_CUSTOM_DOMAIN")

def upload_bytes(prefix: str, data: bytes, ext: str = "jpg") -> str:
    key = f"{prefix}{uuid.uuid4()}.{ext}"
    s3.upload_fileobj(
        io.BytesIO(data),
        BUCKET,
        key,
        ExtraArgs={
            "ContentType": f"image/{ext}",
            "ContentDisposition": "inline",
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
