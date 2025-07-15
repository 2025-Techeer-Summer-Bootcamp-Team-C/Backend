from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.generics import CreateAPIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Product, ProductImage
from .serializers import ProductCreateSerializer
from .utils import upload_product_image  # ✅ 수정된 함수 임포트
from fitting.models import FittingResult


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

class ProductImageUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="상품 이미지 다중 업로드",
        operation_description="상품 ID에 해당하는 상품에 여러 장의 이미지를 업로드하고 DB에 저장합니다.",
        manual_parameters=[
            openapi.Parameter(
                name='images',
                in_=openapi.IN_FORM,
                description='업로드할 이미지 파일들 (다중 업로드)',
                type=openapi.TYPE_FILE,
                required=True
            )
        ],
        responses={201: "업로드 성공", 400: "잘못된 요청", 404: "상품 없음"},
    )
    def post(self, request, product_id):
        product = Product.objects.filter(id=product_id).first()
        if not product:
            return Response({"error": "상품이 존재하지 않습니다."}, status=404)

        files = request.FILES.getlist('images')
        if not files:
            return Response({"error": "업로드할 이미지가 없습니다."}, status=400)

        uploaded_urls = []

        for image_file in files:
            image_bytes = image_file.read()
            s3_url = upload_product_image(product.id, image_bytes)

            # ✅ ProductImage DB 저장 (is_deleted=False로 명시)
            ProductImage.objects.create(
                product=product,
                image=s3_url,
                is_deleted=False  # 기본값 지정
            )

            uploaded_urls.append(s3_url)

        return Response({
            "product_id": product.id,
            "uploaded_images": uploaded_urls
        }, status=201)
        
class ProductInfoListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="상품 정보 리스트 (스위치 기반 대표 이미지 변경)",
        operation_description="""
        - show_fitting=false: product 테이블에서 대표 이미지 및 상세 설명 반환<br/>
        - show_fitting=true: fitting_result 테이블의 이미지 및 상세 설명 반환
        """,
        manual_parameters=[
            openapi.Parameter(
                'show_fitting',
                openapi.IN_QUERY,
                description="true: 피팅 이미지, false: 상품 모델 이미지",
                type=openapi.TYPE_BOOLEAN,
                required=True
            )
        ]
    )
    def get(self, request):
        show_fitting = request.GET.get('show_fitting', 'false').lower() == 'true'
        result = []

        if show_fitting:
            # 피팅 결과 이미지 2개
            fittings = FittingResult.objects.filter(is_deleted=False).select_related('product')[:2]
            for fitting in fittings:
                product = fitting.product
                result.append({
                    'product_id': product.id,
                    'name': product.name,
                    'price': product.price,
                    'image': fitting.image if fitting.image else product.image,
                    'content': product.content
                })
        else:
            # 상품(models.Product) 이미지 2개
            products = Product.objects.filter(is_deleted=False)[:2]
            for product in products:
                result.append({
                    'product_id': product.id,
                    'name': product.name,
                    'price': product.price,
                    'image': product.image,
                    'content': product.content
                })

        return Response({'products': result}, status=200)