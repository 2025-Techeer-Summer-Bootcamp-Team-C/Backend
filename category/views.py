from product.models import Category
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_yasg.utils import swagger_auto_schema

from product.models import Category
from .serializers import CategoryWithProductsSerializer, CategoryCreateSerializer

from drf_yasg import openapi

class CategoryProductByIdView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="특정 카테고리 상품 조회",
        operation_description="요청 쿼리 파라미터(category) 값에 해당하는 카테고리의 상품 리스트 반환",
        manual_parameters=[
            openapi.Parameter(
                'category', openapi.IN_QUERY, description="카테고리 ID(아우터:1, 상의:2, 하의:3)", type=openapi.TYPE_INTEGER, required=True
            )
        ],
        responses={200: CategoryWithProductsSerializer()}
    )
    def get(self, request):
        category_id = request.GET.get('category')
        if category_id is None:
            return Response({'status': 400, 'message': 'category 값이 필요합니다.'}, status=400)

        try:
            category = Category.objects.prefetch_related('product_set').get(id=category_id)
        except Category.DoesNotExist:
            return Response({'status': 404, 'message': '해당 카테고리는 존재하지 않습니다.'}, status=404)

        serializer = CategoryWithProductsSerializer(category)
        return Response({
            'status': 200,
            'message': f'카테고리(ID={category_id}) 상품 리스트 조회 성공',
            'data': serializer.data
        }, status=200)

class CategoryCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="카테고리 생성",
        operation_description="정수 형태의 카테고리 ID를 받아 새로운 카테고리를 생성합니다.",
        request_body=CategoryCreateSerializer,
        responses={
            201: openapi.Response(
                description="생성 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(description="잘못된 요청"),
        }
    )
    def post(self, request):
        # 요청 데이터 검증 및 저장
        serializer = CategoryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "카테고리가 생성되었습니다."},
            status=status.HTTP_201_CREATED
        )

