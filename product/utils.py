import os, io, uuid, boto3

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_S3_REGION_NAME"),
)

BUCKET = os.getenv("AWS_STORAGE_BUCKET_NAME")
CLOUDFRONT_DOMAIN = os.getenv("AWS_S3_CUSTOM_DOMAIN")


def upload_product_image(product_id: int, image_bytes: bytes, ext: str = "jpg") -> str:
    """
    상품 ID 기반으로 S3에 이미지 저장 후 CloudFront URL 반환
    model_images/{product_id}/{uuid}.jpg 형식
    """
    key = f"model_images/{product_id}/{uuid.uuid4()}.{ext}"
    s3.upload_fileobj(
        io.BytesIO(image_bytes),
        BUCKET,
        key,
        ExtraArgs={
            "ContentType": f"image/{ext}",
            "ContentDisposition": "inline",
        },
    )
    return f"{CLOUDFRONT_DOMAIN}/{key}"

def upload_product_image(product_id: int, image_bytes: bytes, ext: str = "jpg") -> str:
    """
    상품 ID 하위로 이미지를 저장하고 CloudFront URL 반환
    product_images/{product_id}/{uuid}.jpg
    """
    key = f"product_images/{product_id}/{uuid.uuid4()}.{ext}"
    s3.upload_fileobj(
        io.BytesIO(image_bytes),
        BUCKET,
        key,
        ExtraArgs={
            "ContentType": f"image/{ext}",
            "ContentDisposition": "inline",
        },
    )
    return f"{CLOUDFRONT_DOMAIN}/{key}"
