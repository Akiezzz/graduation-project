from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import Merchant
from .serializers import MerchantSerializer
from product.models import Product, Category
from product.serializers import ProductSerializer
from order.models import Order
from order.serializers import OrderSerializer


def get_merchant(user):
    try:
        return Merchant.objects.get(user=user)
    except Merchant.DoesNotExist:
        return None


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def api_merchant_products(request):
    merchant = get_merchant(request.user)
    if not merchant:
        return Response({'error': '您不是商家'}, status=403)
    if request.method == 'GET':
        products = Product.objects.filter(merchant=merchant)
        return Response(ProductSerializer(products, many=True).data)
    if not merchant.is_approved:
        return Response({'error': '店铺未审核通过'}, status=403)
    data = request.data.copy()
    s = ProductSerializer(data=data)
    if s.is_valid():
        s.save(merchant=merchant)
        return Response(s.data, status=201)
    return Response(s.errors, status=400)


@api_view(['PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def api_merchant_product_detail(request, pk):
    merchant = get_merchant(request.user)
    if not merchant:
        return Response({'error': '您不是商家'}, status=403)
    try:
        product = Product.objects.get(pk=pk, merchant=merchant)
    except Product.DoesNotExist:
        return Response({'error': '商品不存在'}, status=404)
    if request.method == 'DELETE':
        product.delete()
        return Response(status=204)
    s = ProductSerializer(product, data=request.data, partial=True)
    if s.is_valid():
        s.save()
        return Response(s.data)
    return Response(s.errors, status=400)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def api_merchant_orders(request):
    merchant = get_merchant(request.user)
    if not merchant:
        return Response({'error': '您不是商家'}, status=403)
    orders = Order.objects.filter(items__product__merchant=merchant).distinct().order_by('-created_at')
    return Response(OrderSerializer(orders, many=True).data)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def api_merchant_profile(request):
    merchant = get_merchant(request.user)
    if request.method == 'GET':
        if not merchant:
            return Response({'error': '未申请商家'}, status=404)
        return Response(MerchantSerializer(merchant).data)
    # POST: apply
    if merchant:
        return Response({'error': '已申请过商家'}, status=400)
    s = MerchantSerializer(data=request.data)
    if s.is_valid():
        s.save(user=request.user)
        return Response(s.data, status=201)
    return Response(s.errors, status=400)
