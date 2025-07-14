from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.generics import CreateAPIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.response import Response

from .models import Product
from .serializers import ProductCreateSerializer
from .utils import upload_product_image  # ✅ 수정된 함수 임포트


class ProductCreateView(CreateAPIView):
    permission_classes = [AllowAny]
    queryset = Product.objects.all()
    serializer_class = ProductCreateSerializer
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        operation_summary="상품 등록 (관리자 전용)",
        operation_description="상품 정보와 로컬 이미지를 업로드하여 상품을 등록합니다.",
        manual_parameters=[
            openapi.Parameter('category', openapi.IN_FORM, description="카테고리 ID", type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('name', openapi.IN_FORM, description="상품명", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('content', openapi.IN_FORM, description="상세 설명", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('price', openapi.IN_FORM, description="가격", type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('count', openapi.IN_FORM, description="재고 수량", type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('image_file', openapi.IN_FORM, description="상품 이미지 파일", type=openapi.TYPE_FILE, required=True),
        ],
        responses={201: "상품 생성 성공", 400: "잘못된 요청"},
    )
    def post(self, request, *args, **kwargs):
        image_file = request.FILES.get('image_file')
        if not image_file:
            return Response({"error": "이미지 파일이 필요합니다."}, status=400)

        # ✅ Step 1. 상품 데이터 저장 (이미지 제외)
        product = Product.objects.create(
            category_id=request.POST.get('category'),
            name=request.POST.get('name'),
            content=request.POST.get('content'),
            price=request.POST.get('price'),
            count=request.POST.get('count'),
            image=''
        )

        # ✅ Step 2. 이미지 S3 업로드 (상품 ID 사용)
        image_bytes = image_file.read()
        s3_url = upload_product_image(product.id, image_bytes)

        # ✅ Step 3. 업로드된 URL로 상품 업데이트
        product.image = s3_url
        product.save()

        return Response({
            "message": "상품이 성공적으로 등록되었습니다.",
            "product_id": product.id,
            "s3_image_url": s3_url
        }, status=201)
