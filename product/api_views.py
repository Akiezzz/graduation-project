from rest_framework import generics, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import Product, Category, ProductReview
from .serializers import ProductSerializer, CategorySerializer, ProductReviewSerializer
from order.models import OrderItem
from recommendation.models import UserBehavior
from recommendation.services import log_user_behavior


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class ProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description', 'keywords']

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category_id=category)
        return qs.order_by('-created_at')


class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]


@api_view(['GET', 'POST'])
def product_reviews(request, pk):
    product = Product.objects.get(pk=pk)
    if request.method == 'GET':
        reviews = product.reviews.all().order_by('-created_at')
        return Response(ProductReviewSerializer(reviews, many=True).data)
    if not request.user.is_authenticated:
        return Response({'error': '请先登录'}, status=401)
    has_completed_order = OrderItem.objects.filter(
        order__user=request.user,
        order__status='completed',
        product=product,
    ).exists()
    if not has_completed_order:
        return Response({'error': '仅已完成订单用户可评价'}, status=400)
    s = ProductReviewSerializer(data=request.data)
    if s.is_valid():
        ProductReview.objects.update_or_create(
            product=product, user=request.user,
            defaults={'rating': s.validated_data['rating'], 'content': s.validated_data.get('content', '')}
        )
        log_user_behavior(request.user, product, UserBehavior.BEHAVIOR_REVIEW)
        return Response(s.data, status=201)
    return Response(s.errors, status=400)
