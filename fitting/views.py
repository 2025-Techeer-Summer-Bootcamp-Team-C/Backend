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
from .tasks import run_vto_task, collect_paths, run_vto_url_task, save_to_s3_and_db, run_vto_edit_url_task, edit_bg_task
from .utils      import upload_bytes, upload_url
from .models     import UserImage
from celery import group, chain
from product.models import Product
from django.core.files.uploadedfile import UploadedFile

load_dotenv()
BITSTUDIO_API_KEY = os.getenv("BITSTUDIO_API_KEY")

class VTOOneShotView(GenericAPIView):
    permission_classes = [IsAuthenticated]
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
        
        user_s3_url = upload_bytes("user/", data["person_image"].read())
        
        data["person_image"].seek(0)
        
        user_img_obj = UserImage.objects.create(
            user_id=request.user if request.user.is_authenticated else None,
            user_image_url=user_s3_url
        )

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

        vto_s3_url = upload_url("vto/", paths[0])

        # 6-B) 피팅 결과 DB 저장
        fit_obj = FittingResult.objects.create(
            user_image=user_img_obj,
            fitting_photo_url=vto_s3_url
            )
        
        return Response({
            "paths": paths,
            "fitting_id": fit_obj.id,
            "vto_image_s3": vto_s3_url,
            "user_image_s3": user_s3_url,
            })

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
    
class VTOProductView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = GenerateVTOProductRequestSerializer

    @swagger_auto_schema(
        operation_summary="상품-URL VTO (2장 병렬)",
        request_body=GenerateVTOProductRequestSerializer,   # ← 새 스키마
        responses={200: openapi.Response("OK")},
    )
    def post(self, request):
        # 1) 입력 검증
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        person_url  = data["person_image_url"]
        outfit_url  = data["outfit_image_url"]
        category    = data["category"]        # 상의 / 하의 / 기타

        # 2) 카테고리에 따라 안내 문구(garment_clause) 결정
        if category == "상의":
            garment_clause = (
                "Replace only the upper garment with the input clothing, "
                "leaving all other clothes unchanged. "
            )
        elif category == "하의":
            garment_clause = (
                "Replace only the lower garment with the input clothing, "
                "leaving all other clothes unchanged. "
            )
        else:
            garment_clause = ""

        # 3) 공통 프롬프트 (category 반영)
        base_prompt = (
            "Generate a realistic, high-quality full-body image of the input person "
            "wearing the input clothing. "
            f"{garment_clause}"
            "Ensure the clothes fit naturally to the body shape and preserve the "
            "person's facial features, skin tone, and hair. "
        )

        prompts = [
            base_prompt,                                  # ① 현재 자세
            "Standing at attention. " + base_prompt,      # ② 차렷 자세
        ]

        # 4) Celery chord (2개 병렬)
        header = [
            run_vto_url_task.s(person_url, outfit_url, p)
            for p in prompts
        ]
        result_async = chord(header)(collect_paths.s())

        try:
            paths = result_async.get(timeout=120)  # [path1, path2] or None
        except Exception as exc:
            return Response(
                {"error": f"VTO 작업 수집 실패: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if any(p is None for p in paths):
            return Response(
                {"error": "VTO 생성 실패/타임아웃", "paths": paths},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"paths": paths}, status=200)
    
class VTOTestView(GenericAPIView):
    """
    로컬 사진 2장을 받아 Bitstudio VTO 1장을 동기식 생성 →  
    ① 사용자 원본 사진 S3 업로드  
    ② Bitstudio 결과 이미지를 S3 재업로드  
    ③ 두 URL을 DB(UserImage, FittingResult)에 저장 후 반환
    """
    permission_classes = [IsAuthenticated]
    parser_classes     = [parsers.MultiPartParser, parsers.FormParser]
    serializer_class   = VTOTestRequestSerializer

    # Swagger 수동 파라미터
    file_param = lambda self, name, desc: openapi.Parameter(
        name=name, in_=openapi.IN_FORM, description=desc,
        type=openapi.TYPE_FILE, required=True
    )

    @swagger_auto_schema(
        operation_summary="VTO 테스트 (파일 2장 → 결과 1장, S3 저장)",
        consumes=["multipart/form-data"],
        manual_parameters=[
            file_param(None, "person_image",  "사람 전신 이미지"),
            file_param(None, "outfit_image",  "의상(상품) 이미지"),
        ],
        responses={200: openapi.Response("OK")},
    )
    def post(self, request):
        # 1) 입력 검증
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        files = ser.validated_data

        # 2) 사용자 원본 사진 S3 업로드 & DB 저장 --------------------------
        user_s3_url = upload_bytes("user/", files["person_image"].read())
        
        files["person_image"].seek(0)
        
        user_img_obj = UserImage.objects.create(
            user_id=request.user if request.user.is_authenticated else None,
            user_image_url=user_s3_url
        )

        # 3) Bitstudio 업로드(파일) → image_id 확보 ------------------------
        person_id = self._upload_image(files["person_image"], "virtual-try-on-person")
        outfit_id = self._upload_image(files["outfit_image"], "virtual-try-on-outfit")

        # 4) 단일 프롬프트
        prompt = (
            "Generate a realistic, high-quality full-body image of the input person "
            "wearing the input clothing. Ensure natural fit and preserve facial features."
        )

        # 5) Bitstudio 동기 호출·폴링 ------------------------------
        result_path = self._run_vto_inline(person_id, outfit_id, prompt)
        if result_path is None:
            return Response(
                {"error": "VTO 생성 실패/타임아웃"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 6) Bitstudio 결과 S3 재업로드 & DB 저장 -------------------
        vto_s3_url = upload_url("vto/", result_path)
        fit_obj = FittingResult.objects.create(
            user_image        = user_img_obj,
            fitting_photo_url = vto_s3_url
        )

        return Response(
            {
                "user_image_s3": user_s3_url,
                "vto_image_s3":  vto_s3_url,
                "fitting_id":    fit_obj.id
            },
            status=200,
        )

    # ───────────────────────── helper methods ─────────────────────
    @staticmethod
    def _upload_image(file_obj, img_type):
        r = requests.post(
            "https://api.bitstudio.ai/images",
            headers={"Authorization": f"Bearer {BITSTUDIO_API_KEY}"},
            files={"file": file_obj, "type": (None, img_type)},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["id"]

    @staticmethod
    def _run_vto_inline(person_id, outfit_id, prompt) -> str | None:
        try:
            r = requests.post(
                "https://api.bitstudio.ai/images/virtual-try-on",
                headers={"Authorization": f"Bearer {BITSTUDIO_API_KEY}",
                         "Content-Type":  "application/json"},
                json={
                    "person_image_id": person_id,
                    "outfit_image_id": outfit_id,
                    "prompt":         prompt,
                    "resolution":     "standard",
                    "num_images":     1,
                    "style":          "studio",
                },
                timeout=30,
            )
            r.raise_for_status()
            job_id = r.json()[0]["id"]

            for _ in range(30):         # 2초 × 30 = 60초
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
            return None
        except Exception:
            return None
        
class ProductFittingGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        person_url = user.profile_image
        if not person_url:
            return Response({"error": "사용자 사진이 없습니다."}, status=400)

        products = Product.objects.all()
        if not products.exists():
            return Response({"error": "상품이 없습니다."}, status=400)

        prompt = "Using the outfit image as the pose, lighting, and background reference, replace the model with the input person so that the person now wears the same clothes in the exact pose and setting. Preserve the model photo’s camera angle, framing, and white-studio background, but swap in the input person’s face, skin tone, hair, and body proportions. Ensure the clothes fit naturally to the new body and the overall result looks realistic and high-quality."
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
        
TNB_BG_API   = "https://thenewblack.ai/api/1.1/wf/change-background"
TNB_EMAIL    = os.getenv("TNB_EMAIL")      # The New Black 계정
TNB_PASSWORD = os.getenv("TNB_PASSWORD")

class RemoveBgView(APIView):
    """
    The New Black AI 'change-background' 테스트 프록시
    배경을 흰색 스튜디오로 교체하고 TNB가 돌려준 응답 그대로 반환
    """
    permission_classes = [AllowAny]          # 공개 테스트용
    parser_classes     = (MultiPartParser, FormParser)   # 파일·URL 둘 다 수용

    # ───────────────────────── Swagger ──────────────────────────
    @swagger_auto_schema(
        operation_summary="TNB 배경 교체(흰색 스튜디오) 테스트",
        request_body=ChangeBgSerializer,
        responses={200: openapi.Response("TNB 원본 응답(JSON 또는 텍스트)")},
    )
    def post(self, request):
        # 1) 입력 검증
        ser = ChangeBgSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        # 2) multipart 인자 구성
        files = {
            "email":    (None, TNB_EMAIL or request.data.get("email")),
            "password": (None, TNB_PASSWORD or request.data.get("password")),
            "image":    self._as_file_tuple(d["image"]),       # 핵심
            "replace":  (None, "pure white seamless studio backdrop, no objects"), 
        }
        if d.get("negative"):
            files["negative"] = (None, d["negative"])

        # 3) TNB 호출
        try:
            resp = requests.post(TNB_BG_API, files=files, timeout=90)
        except requests.RequestException as exc:
            return Response(
                {"error": f"TNB 요청 실패: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # 4) 원본 응답을 그대로 전달 (JSON/텍스트 자동 구분)
        body = self._safe_body(resp)
        return Response(body, status=resp.status_code)

    # ──────────────── helpers ──────────────────────────────────
    @staticmethod
    def _as_file_tuple(value):
        """
        value 가
        ▸ UploadedFile  → ("filename", file_obj)
        ▸ str(URL)      → (None, url_string)
        로 변환해 multipart form에 넣는다.
        """
        if isinstance(value, UploadedFile):
            return (value.name, value)
        return (None, value)

    @staticmethod
    def _safe_body(resp):
        """
        JSON이면 파싱, 아니면 텍스트 그대로 반환.
        "raw" 키에 본문을 담아줌.
        """
        content_type = resp.headers.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                return resp.json()
            except ValueError:
                return {"raw": resp.text, "note": "JSON 파싱 실패"}
        return {"raw": resp.text}
    
    
import logging
logger = logging.getLogger(__name__)
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
        person_url = user.profile_image
        if not person_url:
            return Response({"error": "사용자 사진이 없습니다."}, status=400)

        products = Product.objects.all()
        if not products.exists():
            return Response({"error": "상품이 없습니다."}, status=400)

        prompt = "Using the outfit image as the pose, lighting, and background reference, replace the model with the input person so that the person now wears the same clothes in the exact pose and setting. Preserve the model photo’s camera angle, framing, and white-studio background, but swap in the input person’s face, skin tone, hair, and body proportions. Ensure the clothes fit naturally to the new body and the overall result looks realistic and high-quality."
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