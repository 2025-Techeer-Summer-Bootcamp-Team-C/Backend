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
from .serializers import GenerateVTORequestSerializer, VTORequestSerializer
import requests
from rest_framework.permissions import AllowAny
from celery import chord
from .tasks import run_vto_task, collect_paths

BITSTUDIO_API_KEY = os.getenv("BITSTUDIO_API_KEY")
load_dotenv()

class VTOOneShotView(GenericAPIView):
    permission_classes = [AllowAny]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    serializer_class = VTORequestSerializer

    # Swagger 수동 파라미터
    file_param = lambda self, name, desc: openapi.Parameter(
        name=name, in_=openapi.IN_FORM, description=desc,
        type=openapi.TYPE_FILE, required=True
    )
    str_param = lambda self, name, desc: openapi.Parameter(
        name=name, in_=openapi.IN_FORM, description=desc,
        type=openapi.TYPE_STRING, required=True
    )

    @swagger_auto_schema(
        operation_summary="One-shot VTO (4 variations)",
        consumes=["multipart/form-data"],
        manual_parameters=[
            file_param(None, "person_image", "사람 전신 이미지"),
            file_param(None, "outfit_image", "의상 이미지"),
            str_param(None, "category", "카테고리 (상의/하의/기타)"),
            str_param(None, "detail",   "세부 예: 반팔"),
            str_param(None, "fit",      "핏 예: 스탠다드핏"),
            str_param(None, "length",   "기장 예: 기본"),
        ],
        responses={200: openapi.Response("OK")},
    )
    def post(self, request):
        # 0) 유효성 검증
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        # 1) 이미지 업로드(두 장)
        person_id = self._upload_image(
            data["person_image"], img_type="virtual-try-on-person"
        )
        outfit_id = self._upload_image(
            data["outfit_image"], img_type="virtual-try-on-outfit"
        )

        # 2) 공통 프롬프트 구성
        meta_txt = (
            f'Category: {data["category"]}, Detail: {data["detail"]}, '
            f'Fit: {data["fit"]}, Length: {data["length"]}'
        )
        if data["category"] == "상의":
            garment_clause = (
                "Replace only the upper garment with the input clothing, "
                "leaving all other clothes unchanged."
            )
        elif data["category"] == "하의":
            garment_clause = (
                "Replace only the lower garment with the input clothing, "
                "leaving all other clothes unchanged."
            )
        else:
            garment_clause = "Replace the input clothing as requested."

        base_prompt = (
            "Generate a realistic, high-quality full-body image of the input person "
            "wearing the input clothing. "
            f"{garment_clause} Ensure the clothes fit naturally to the body shape and "
            "preserve the person's facial features, skin tone, and hair. "
            f"({meta_txt}) "
        )

        # 3) 프롬프트 4종
        prompts = [
            "Frontal studio shot. " + base_prompt,
            "Frontal shot, arms crossed. " + base_prompt,
            "Frontal shot, hands in pockets. " + base_prompt,
            "Standing at attention. " + base_prompt,
]

        # 4) Celery chord 실행
        header = [run_vto_task.s(person_id, outfit_id, p) for p in prompts]
        async_result = chord(header)(collect_paths.s())  # 병렬 실행 + 콜백

        # 5) 결과 수집 (최대 120초 대기)
        try:
            paths: list[str | None] = async_result.get(timeout=120)
        except Exception as exc:
            return Response(
                {"error": f"작업 수집 중 오류: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 6) 실패 여부 확인
        if any(p is None for p in paths):
            return Response(
                {"error": "일부 VTO 작업이 실패하거나 타임아웃되었습니다.", "paths": paths},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"paths": paths})

    # ───────────────────────── helper methods ─────────────────────
    @staticmethod
    def _upload_image(file_obj, img_type: str) -> str:
        """Bitstudio 이미지 업로드 → image_id 반환"""
        res = requests.post(
            "https://api.bitstudio.ai/images",
            headers={"Authorization": f"Bearer {BITSTUDIO_API_KEY}"},
            files={"file": file_obj, "type": (None, img_type)},
            timeout=30,
        )
        res.raise_for_status()
        return res.json()["id"]