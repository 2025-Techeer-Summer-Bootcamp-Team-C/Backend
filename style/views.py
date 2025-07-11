import requests as pyrequests  # 이름 충돌 방지용
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from .serializers import GeminiStyleURLSerializer, GeminiStyleResultSerializer, ShoppingSearchRequestSerializer, ShoppingSearchResponseSerializer
import google.generativeai as genai
from rest_framework.permissions import AllowAny
import os
from dotenv import load_dotenv
import requests

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

KOREAN_SHOPPING_SOURCES = [
    "musinsa", "무신사", "ssg.com", "ssg", "shinsegaemall.ssg.com",
    "11st.co.kr", "11번가", "gmarket.co.kr", "g마켓", "auction.co.kr", "옥션",
    "coupang.com", "쿠팡", "lotteon.com", "롯데온", "interpark.com", "인터파크",
    "wemakeprice.com", "위메프", "akmall.com", "ak몰", "uniqlo.kr", "유니클로",
    "wconcept.co.kr", "w컨셉", "brandi.co.kr", "브랜디", "zigzag.kr", "지그재그",
    "29cm.co.kr", "29cm", "29cm.kr", "musinsastandard", "무신사스탠다드",
    "hiver.co.kr", "하이버", "abcmart.co.kr", "abc마트", "tenbyten.co.kr", "텐바이텐",
    "aladin.co.kr", "알라딘", "yes24.com", "예스24", "gsshop.com", "gs샵",
    "cjmall.com", "cjmall", "sshomeplus.com", "홈플러스", "oliveyoung.co.kr",
    "electronicland.co.kr", "전자랜드", "danawa.com", "다나와", "naver.com", "네이버쇼핑",
    "smartstore.naver.com", "스마트스토어",
]

class GoogleShoppingSearchView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Gemini 기반 구글 쇼핑 상품 탐색",
        request_body=ShoppingSearchRequestSerializer,
        responses={200: ShoppingSearchResponseSerializer}
    )
    def post(self, request):
        category = request.data.get('category')
        detail = request.data.get('detail')
        message = request.data.get('message')
        if not category or not detail:
            return Response(
                {"status": 400, "message": "category 또는 detail 값이 누락되었습니다"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Gemini로 검색어 생성
            gemini_model = genai.GenerativeModel("gemini-1.5-pro")
            prompt = (
                f"카테고리: {category}, 상세: {detail}, 메세지: {message}, 에 맞는 구글 쇼핑 검색어를 한글로 1개만 만들어줘."
            )
            gemini_response = gemini_model.generate_content([{"text": prompt}])
            refined_query = gemini_response.text.strip()
        except Exception as e:
            return Response(
                {"status": 500, "message": f"Gemini API 호출 실패: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        serp_api_key = os.getenv("SERP_API_KEY")
        if not serp_api_key:
            return Response(
                {"status": 500, "message": "SERP_API_KEY가 설정되어 있지 않습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        params = {
            "engine": "google_shopping",
            "q": refined_query,
            "api_key": serp_api_key,
            "hl": "ko",
            "gl": "kr",
            "google_domain": "google.co.kr",
            "num": "50",
        }
        print(refined_query)
        try:
            response = requests.get("https://serpapi.com/search", params=params)
            if response.status_code != 200:
                return Response(
                    {"status": 500, "message": "SerpAPI 호출 실패", "detail": response.text},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            data = response.json()
            shopping_results = data.get("shopping_results", [])
        except Exception as e:
            return Response(
                {"status": 500, "message": f"상품 검색 API 호출 실패: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        results = []
        for item in shopping_results:
            source = (item.get("source") or "").lower()
            if not any(korean_source in source for korean_source in KOREAN_SHOPPING_SOURCES):
                continue

            link = item.get("link")
            product_id = item.get("product_id")
            if not link and product_id:
                product_api_params = {
                    "engine": "google_product",
                    "product_id": product_id,
                    "api_key": serp_api_key,
                }
                product_response = requests.get("https://serpapi.com/search", params=product_api_params)
                if product_response.status_code == 200:
                    product_data = product_response.json()
                    sellers = product_data.get("sellers_results", {}).get("online_sellers", [])
                    if sellers:
                        link = sellers[0].get("link")

            if not link:
                title_encoded = item.get("title", "").replace(" ", "+")
                if "쿠팡" in source or "coupang" in source:
                    link = f"https://www.coupang.com/np/search?q={title_encoded}"
                elif "무신사" in source or "musinsa" in source:
                    link = f"https://search.musinsa.com/search/musinsa/integration?q={title_encoded}"
                elif "ssg" in source:
                    link = f"https://www.ssg.com/search.ssg?query={title_encoded}"
                elif "g마켓" in source or "gmarket" in source:
                    link = f"https://browse.gmarket.co.kr/search?keyword={title_encoded}"
                elif "옥션" in source or "auction" in source:
                    link = f"https://search.auction.co.kr/search/search.aspx?keyword={title_encoded}"

            results.append({
                "product_id": product_id or "",
                "product_name": item.get("title", ""),
                "price": item.get("price", 0),
                "url": link or "",
                "image_url": item.get("thumbnail", ""),
            })

            if len(results) >= 10:
                break

        if not results:
            return Response(
                {"status": 404, "message": "해당 조건에 맞는 상품을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {"status": 200, "results": results},
            status=status.HTTP_200_OK
        )
