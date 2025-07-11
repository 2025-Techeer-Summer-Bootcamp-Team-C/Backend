import requests as pyrequests  # 이름 충돌 방지용
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from .serializers import GeminiStyleURLSerializer, GeminiStyleResultSerializer
import google.generativeai as genai
from rest_framework.permissions import AllowAny
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class GenerateGeminiStyleView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Gemini 이미지 URL 스타일 키워드 추천",
        request_body=GeminiStyleURLSerializer,
        responses={200: GeminiStyleResultSerializer}
    )
    def post(self, request):
        image_url = request.data.get('image_url')
        if not image_url:
            return Response({"error": "image_url 값이 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. 이미지 다운로드
            img_response = pyrequests.get(image_url)
            if img_response.status_code != 200:
                return Response({"error": "이미지 다운로드 실패"}, status=status.HTTP_400_BAD_REQUEST)
            image_bytes = img_response.content
            mime_type = img_response.headers.get("Content-Type", "image/jpeg")

            # 2. Gemini Vision API 호출
            model = genai.GenerativeModel("gemini-1.5-pro")
            prompt = (
                "아래 이미지를 보고, 이 사람의 패션 스타일을 가장 잘 나타내는 키워드를 5개 선정해 주세요.\n"
                "각 키워드는 반드시 # 기호로 시작해야 하며, 예시처럼 한글로 작성해 주세요.\n"
                "예시: #미니멀 #스트리트 #빈티지 #캐주얼 #모던\n"
                "오직 키워드만, 공백으로 구분해서 5개만 출력해 주세요.\n"
                "참고: 스타일 키워드는 패션 장르, 분위기, 유행, 컬러, 실루엣 등 자유롭게 선정할 수 있습니다."
            )
            contents = [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": image_bytes
                    }
                }
            ]
            response = model.generate_content(contents)
            result_text = response.text.strip() if hasattr(response, "text") else response.candidates[0].content.parts[0].text.strip()
            return Response({"result": result_text}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
