import os, time
from dotenv import load_dotenv
from rest_framework import status, parsers
from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.conf import settings
from openai import OpenAI
from rest_framework.parsers import MultiPartParser, FormParser
import base64
from .serializers import GenerateVTORequestSerializer, VTORequestSerializer, GenerateVTOProductRequestSerializer, VTOTestRequestSerializer, ChangeBgSerializer
import requests
from rest_framework.permissions import AllowAny, IsAuthenticated
from celery import chord
from .tasks import run_vto_url_task, save_to_s3_and_db, run_vto_edit_url_task, edit_bg_task, generate_fitting_video_task
from .utils      import upload_bytes, upload_url
from .models     import UserImage
from celery import group, chain
from product.models import Product
from django.core.files.uploadedfile import UploadedFile
from django.shortcuts import get_object_or_404
from .models import FittingResult
import logging

logger = logging.getLogger(__name__)
load_dotenv()
BITSTUDIO_API_KEY = os.getenv("BITSTUDIO_API_KEY")

class ProductFittingGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.is_fitting:
            return Response(
                {"error": "이미 가상 피팅을 완료했거나 피팅 중입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        person_url = user.profile_image
        if not person_url:
            return Response({"error": "사용자 사진이 없습니다."}, status=400)

        products = Product.objects.all()
        if not products.exists():
            return Response({"error": "상품이 없습니다."}, status=400)

        prompt = "Using the outfit image as the pose, lighting, and background reference, replace the model with the input person so that the person now wears the same clothes in the exact pose and setting. Preserve the model photo’s camera angle, framing, and white-studio background, but swap in the input person’s face, skin tone, hair, and body proportions. Ensure the clothes fit naturally to the new body and the overall result looks realistic and high-quality."
        
        # 시작 시점에 플래그 설정
        user.is_fitting = True
        user.save(update_fields=["is_fitting"])
        
        # 상품별 태스크를 group으로 묶어 한꺼번에 예약
        tasks = [
            chain(
                run_vto_url_task.s(person_url, product.image, prompt),   # ① VTO 생성
                save_to_s3_and_db.s(user.id, product.id)         # ② S3+DB 저장
            )
            for product in products
        ]

        job = group(tasks).apply_async()   # 비동기 예약

        return Response(
            {
                "message": "가상 피팅 작업이 병렬로 예약되었습니다.",
                "task_group_id": job.id,
                "total_products": products.count()
            },
            status=202
        )
    
class EditBgWhiteView(APIView):
    """
    BitStudio Edit Image API를 사용해
    image_id로 지정한 원본 이미지의 **배경을 흰색**으로 바꿉니다.
    """
    permission_classes = [AllowAny]
    parser_classes     = [parsers.JSONParser, parsers.FormParser]

    # -------- 수정 파라미터 --------
    PROMPT      = "Replace the background with a soft light-gray studio backdrop (#e8e8e8) and add a subtle floor shadow under the model for realism"
    RESOLUTION  = "standard"
    NUM_IMAGES  = 1
    SEED        = 4

    # -------- 폴링 설정 --------
    POLL_INTERVAL = 5   # 초
    MAX_POLLS     = 36

    # -------- Swagger 스키마 --------
    @swagger_auto_schema(
        operation_summary="이미지 배경을 흰색으로 편집",
        operation_description="""
BitStudio **Edit Image API**를 호출해 `image_id`에 해당하는 이미지를
plain white 배경으로 변경합니다.

- 200 OK  : 편집 완료, 최종 URL 반환  
- 202     : 30초 내 완료되지 않음(계속 폴링 필요)  
- 400/500 : 요청 실패
""",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["image_id"],
            properties={
                "image_id": openapi.Schema(type=openapi.TYPE_STRING),
            },
            example={"image_id": "IMG_123"}
        ),
        responses={
            200: openapi.Response(description="편집 완료"),
            202: openapi.Response(description="편집 진행 중(타임아웃)"),
            400: openapi.Response(description="BitStudio 요청 실패"),
        },
    )
    # --------------------------------
    def post(self, request):
        image_id = request.data.get("image_id")
        if not image_id:
            return Response(
                {"detail": "image_id 파라미터가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1) 편집 요청
        try:
            edit_resp = requests.post(
                f"https://api.bitstudio.ai/images/{image_id}/edit",
                headers={
                    "Authorization": f"Bearer {BITSTUDIO_API_KEY}",
                    "Content-Type":  "application/json",
                },
                json={
                    "prompt":     self.PROMPT,
                    "resolution": self.RESOLUTION,
                    "num_images": self.NUM_IMAGES,
                    "seed":       self.SEED,
                },
                timeout=60,
            )
        except requests.RequestException as exc:
            logger.exception("BitStudio 편집 요청 네트워크 오류")
            return Response(
                {"detail": "BitStudio 편집 요청 중 네트워크 오류", "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # 2xx 이외 → 실패로 간주
        if not edit_resp.ok:
            return Response(
                {"detail": "BitStudio 편집 요청 실패", "bitstudio_response": edit_resp.text},
                status=status.HTTP_400_BAD_REQUEST,
            )

        edit_data = edit_resp.json()
        logger.debug("BitStudio edit 응답: %s", edit_data)

        # 2) 새로 만들어진 edited 버전 찾기
        edit_versions = [
            v for v in edit_data.get("versions", [])
            if v.get("version_type") in ("edit", "edited")
        ]
        if not edit_versions:
            return Response(
                {"detail": "versions 배열에 edit/edited 항목이 없습니다.",
                 "bitstudio_response": edit_data},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        edit_version = edit_versions[0]
        target_id = edit_version["source_image_id"]

        print(target_id)
        # 3) 편집 완료까지 폴링
        for _ in range(self.MAX_POLLS):
            status_resp = requests.get(
                f"https://api.bitstudio.ai/images/{target_id}",
                headers={"Authorization": f"Bearer {BITSTUDIO_API_KEY}"},
                timeout=30,
            ).json()

            logger.debug("폴링 결과: %s", status_resp)

            if status_resp.get("status") == "completed":
                return Response(
                    {
                        "detail": "편집 완료",
                        "image":  status_resp.get("path"),
                        "meta":   status_resp,
                    },
                    status=status.HTTP_200_OK,
                )
            if status_resp.get("status") == "failed":
                return Response(
                    {"detail": "BitStudio 편집 실패", "meta": status_resp},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            time.sleep(self.POLL_INTERVAL)

        # 4) 타임아웃
        return Response(
            {
                "detail": f"{self.MAX_POLLS * self.POLL_INTERVAL}초 내에 편집이 완료되지 않았습니다.",
                "meta": edit_data,
            },
            status=status.HTTP_202_ACCEPTED,
        )
        
class ProductFittingGenerateDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        if user.is_fitting:
            return Response(
                {"error": "이미 가상 피팅을 완료했거나 피팅 중입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        person_url = user.profile_image
        if not person_url:
            return Response({"error": "사용자 사진이 없습니다."}, status=400)

        products = Product.objects.all()
        if not products.exists():
            return Response({"error": "상품이 없습니다."}, status=400)

        prompt = "Using the outfit image as the pose, lighting, and background reference, replace the model with the input person so that the person now wears the same clothes in the exact pose and setting. Preserve the model photo’s camera angle, framing, and white-studio background, but swap in the input person’s face, skin tone, hair, and body proportions. Ensure the clothes fit naturally to the new body and the overall result looks realistic and high-quality."
        # 시작 시점에 플래그 설정
        user.is_fitting = True
        user.save(update_fields=["is_fitting"])

        # 상품별 태스크를 group으로 묶어 한꺼번에 예약
        tasks = [
            chain(
                run_vto_edit_url_task.s(person_url, product.image, prompt),   # ① VTO 생성
                edit_bg_task.s(),
                save_to_s3_and_db.s(user.id, product.id)         # ② S3+DB 저장
            )
            for product in products
        ]

        job = group(tasks).apply_async()   # 비동기 예약

        return Response(
            {
                "message": "가상 피팅 작업이 병렬로 예약되었습니다.",
                "task_group_id": job.id,
                "total_products": products.count()
            },
            status=202
        )
        
class ProductFittingVideoGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        fitting = get_object_or_404(
            FittingResult,
            user=request.user,
            product=product
        )
        
        if fitting.status == 'processing':
            return Response(
                {"detail": "이미 영상 생성 요청이 진행 중입니다."},
                status=status.HTTP_202_ACCEPTED
            )
        if fitting.status == 'completed' and fitting.video:
            return Response(
                {
                    "detail": "이미 영상이 생성되어 있습니다.",
                    "video_url": fitting.video
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # 외부 API에 작업 요청만 보내고 external_id 만 저장
        resp = requests.post(
            "https://thenewblack.ai/api/1.1/wf/ai-video",
            files={
                'email':    (None, os.getenv("TNB_EMAIL")),
                'password': (None, os.getenv("TNB_PASSWORD")),
                'image':    (None, fitting.image),
                'prompt':   (None, "A full‑body shot of a professional fashion model gracefully alternating between left and right poses on a minimalist studio background, with soft directional lighting highlighting the contours of the clothing, high resolution, ultra‑realistic detail, while preserving the model’s facial features and the precise fit of the clothing."),
            }
        )
        if resp.status_code != 200:
            return Response({"detail": resp.text}, status=resp.status_code)

        task_id = resp.text.strip()
        if not task_id:
            return Response(
                {"detail": "외부 작업 ID를 받을 수 없습니다. 응답: " + resp.text},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
        fitting.status = 'processing'
        fitting.save(update_fields=['status'])

        # Celery 태스크 비동기로 호출
        generate_fitting_video_task.delay(fitting.id, task_id)

        return Response(
            {"detail": "영상 생성 요청을 받았습니다. 잠시 후 상태를 확인하세요."},
            status=status.HTTP_202_ACCEPTED
        )
        
class ProductFittingVideoStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=None,
        manual_parameters=[
            openapi.Parameter(
                'product_id', openapi.IN_PATH,
                description="피팅 대상 상품 ID",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={200: openapi.Response(
            '현재 상태 및 비디오 URL',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status':    openapi.Schema(type=openapi.TYPE_STRING, description='pending|processing|completed|failed'),
                    'video_url': openapi.Schema(type=openapi.TYPE_STRING, description='완료 시 S3 비디오 URL, 그 외 null'),
                }
            )
        )}
    )
    def get(self, request, product_id):
        # 1) 레코드 존재 확인
        product = get_object_or_404(Product, pk=product_id)
        fitting = get_object_or_404(FittingResult, user=request.user, product=product)

        # 2) 응답
        return Response({
            'status':    fitting.status,
            'video_url': fitting.video if fitting.status == 'completed' else None
        }, status=status.HTTP_200_OK)