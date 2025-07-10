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
    MAX_POLLS     = 15  # 2 × 15 = 30초 (작업당)

    # ── Swagger 수동 파라미터 --------------------------------------
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
        # 0) 유효성 검사
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        # 1) 이미지 업로드
        person_id = self._upload_image(data["person_image"], "virtual-try-on-person")
        outfit_id = self._upload_image(data["outfit_image"], "virtual-try-on-outfit")

        # 2) 공통 메타·가먼트 클로즈
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

        # 3) 프롬프트 4종(연출/각도 예시)
        prompt_variations = [
            base_prompt + "Frontal studio shot.",
            base_prompt + "45-degree left angle view.",
            base_prompt + "45-degree right angle view.",
            base_prompt + "Back view showcasing garment fit.",
        ]

        paths = []  # 최종 URL 모음

        for prompt in prompt_variations:
            # 3-1) VTO 호출
            job_id = self._start_vto_job(person_id, outfit_id, prompt)

            # 3-2) 완료까지 폴링
            path = self._wait_for_completion(job_id)
            if path is None:       # 실패 처리
                return Response(
                    {"error": f"Job {job_id} failed or timed out"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            paths.append(path)

        # 4) 완료 → path 리스트 반환
        return Response({"paths": paths})

    # ─────────────────────────────── helper funcs ──────────────────
    @staticmethod
    def _upload_image(file_obj, img_type):
        res = requests.post(
            "https://api.bitstudio.ai/images",
            headers={"Authorization": f"Bearer {BITSTUDIO_API_KEY}"},
            files={"file": file_obj, "type": (None, img_type)},
            timeout=30,
        )
        res.raise_for_status()
        return res.json()["id"]

    def _start_vto_job(self, person_id, outfit_id, prompt):
        payload = {
            "person_image_id": person_id,
            "outfit_image_id": outfit_id,
            "prompt": prompt,
            "resolution": "standard",
            "num_images": 1,
            "style": "studio",
        }
        res = requests.post(
            "https://api.bitstudio.ai/images/virtual-try-on",
            headers={
                "Authorization": f"Bearer {BITSTUDIO_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        res.raise_for_status()
        return res.json()[0]["id"]

    def _wait_for_completion(self, job_id):
        """완료 시 path 반환, 실패/타임아웃 시 None"""
        for _ in range(self.MAX_POLLS):
            res = requests.get(
                f"https://api.bitstudio.ai/images/{job_id}",
                headers={"Authorization": f"Bearer {BITSTUDIO_API_KEY}"},
                timeout=10,
            )
            res.raise_for_status()
            info = res.json()
            if info.get("status") == "completed":
                return info.get("path")
            if info.get("status") == "failed":
                return None
            time.sleep(self.POLL_INTERVAL)
        return None  # 타임아웃