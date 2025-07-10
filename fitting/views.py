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

BITSTUDIO_API_KEY = os.getenv("BITSTUDIO_API_KEY")
load_dotenv()

class VTOOneShotView(GenericAPIView):
    permission_classes = [AllowAny]
    parser_classes   = [parsers.MultiPartParser, parsers.FormParser]
    serializer_class = VTORequestSerializer

    POLL_INTERVAL = 2   # 초
    MAX_POLLS     = 15  # 2×15 = 30초

    # Swagger 수동 파라미터 (파일 2 + 문자열 4)
    file_param = lambda self, name, desc: openapi.Parameter(
        name=name,
        in_=openapi.IN_FORM,
        description=desc,
        type=openapi.TYPE_FILE,
        required=True,
    )
    str_param = lambda self, name, desc: openapi.Parameter(
        name=name,
        in_=openapi.IN_FORM,
        description=desc,
        type=openapi.TYPE_STRING,
        required=True,
    )

    @swagger_auto_schema(
        operation_summary="One-shot VTO 이미지 생성",
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
        # ── 0. 유효성 검사 ──────────────────────────
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        # ── 1. 이미지 업로드 ────────────────────────
        person_id = self._upload_image(data["person_image"], "virtual-try-on-person")
        outfit_id = self._upload_image(data["outfit_image"], "virtual-try-on-outfit")

        # ── 2. 프롬프트 생성 ────────────────────────
        meta_txt = (
            f'Category: {data["category"]}, Detail: {data["detail"]}, '
            f'Fit: {data["fit"]}, Length: {data["length"]}'
        )

        # 상의·하의만 교체 분기
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

        prompt = (
            "Generate a realistic, high-quality full-body image of the input person "
            "wearing the input clothing. "
            f"{garment_clause} Ensure the clothes fit naturally to the body shape and "
            "preserve the person's facial features, skin tone, and hair. "
            f"({meta_txt})"
        )

        payload = {
            "person_image_id": person_id,
            "outfit_image_id": outfit_id,
            "prompt": prompt,
            "resolution": "standard",
            "num_images": 1,
            "style": "studio",
        }

        vto_res = requests.post(
            "https://api.bitstudio.ai/images/virtual-try-on",
            headers={
                "Authorization": f"Bearer {BITSTUDIO_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        vto_res.raise_for_status()
        job_id = vto_res.json()[0]["id"]

        # ── 3. 폴링 (최대 30초) ─────────────────────
        for _ in range(self.MAX_POLLS):
            job = requests.get(
                f"https://api.bitstudio.ai/images/{job_id}",
                headers={"Authorization": f"Bearer {BITSTUDIO_API_KEY}"},
                timeout=10,
            )
            job.raise_for_status()
            info = job.json()

            if info.get("status") == "completed":
                return Response(info)   # info["path"] → 최종 이미지 URL
            if info.get("status") == "failed":
                return Response(info, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            time.sleep(self.POLL_INTERVAL)

        # ── 4. 30초 초과 → 비동기 전환 ──────────────
        return Response(
            {"job_id": job_id, "status": "processing"},
            status=status.HTTP_202_ACCEPTED,
        )

    # ───────────────────────────────────────────────
    @staticmethod
    def _upload_image(file_obj, img_type):
        """Bitstudio /images 업로드 헬퍼"""
        res = requests.post(
            "https://api.bitstudio.ai/images",
            headers={"Authorization": f"Bearer {BITSTUDIO_API_KEY}"},
            files={"file": file_obj, "type": (None, img_type)},
            timeout=30,
        )
        res.raise_for_status()
        return res.json()["id"]