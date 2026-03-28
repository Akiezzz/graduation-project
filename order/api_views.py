from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Count
from .models import Cart, CartItem, Order, OrderItem
from .serializers import CartItemSerializer, OrderSerializer
from product.models import Product
from recommendation.models import UserBehavior
from recommendation.services import log_user_behavior


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def api_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product').all()
    total = sum(i.product.price * i.quantity for i in items)
    return Response({'items': CartItemSerializer(items, many=True).data, 'total': float(total)})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def api_cart_add(request):
    product_id = request.data.get('product_id')
    quantity = int(request.data.get('quantity', 1))
    product = Product.objects.get(pk=product_id, is_active=True)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        item.quantity += quantity
    else:
        item.quantity = quantity
    item.save()
    log_user_behavior(request.user, product, UserBehavior.BEHAVIOR_CART)
    return Response({'message': '已加入购物车', 'quantity': item.quantity})


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def api_cart_remove(request, item_id):
    CartItem.objects.filter(pk=item_id, cart__user=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def api_orders(request):
    if request.method == 'GET':
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        return Response(OrderSerializer(orders, many=True).data)
    # POST: create order from cart
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product').all()
    if not items:
        return Response({'error': '购物车为空'}, status=400)
    address = request.data.get('address', request.user.address)
    if not address:
        return Response({'error': '请填写收货地址'}, status=400)

    with transaction.atomic():
        product_ids = [item.product_id for item in items]
        products = Product.objects.select_for_update().filter(pk__in=product_ids, is_active=True)
        product_map = {p.id: p for p in products}

        for item in items:
            locked_product = product_map.get(item.product_id)
            if not locked_product:
                return Response({'error': f'商品“{item.product.name}”不可购买'}, status=400)
            if locked_product.stock < item.quantity:
                return Response({'error': f'商品“{locked_product.name}”库存不足'}, status=400)

        order_total = sum(product_map[item.product_id].price * item.quantity for item in items)
        order = Order.objects.create(
            user=request.user, address=address,
            total_price=order_total, remark=request.data.get('remark', '')
        )
        for item in items:
            locked_product = product_map[item.product_id]
            OrderItem.objects.create(order=order, product=locked_product,
                                     quantity=item.quantity, price=locked_product.price)
            log_user_behavior(request.user, locked_product, UserBehavior.BEHAVIOR_ORDER)
            locked_product.stock -= item.quantity
            locked_product.sales += item.quantity
            locked_product.save(update_fields=['stock', 'sales'])
        cart.items.all().delete()
    return Response(OrderSerializer(order).data, status=201)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def api_order_detail(request, pk):
    try:
        order = Order.objects.get(pk=pk, user=request.user)
    except Order.DoesNotExist:
        return Response({'error': '订单不存在'}, status=404)
    return Response(OrderSerializer(order).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def api_order_pay(request, pk):
    try:
        order = Order.objects.get(pk=pk, user=request.user)
    except Order.DoesNotExist:
        return Response({'error': '订单不存在'}, status=404)
    if order.status != 'pending':
        return Response({'error': '当前订单状态不支持支付'}, status=400)
    order.status = 'paid'
    order.save(update_fields=['status'])
    return Response(OrderSerializer(order).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def api_order_cancel(request, pk):
    try:
        order = Order.objects.get(pk=pk, user=request.user)
    except Order.DoesNotExist:
        return Response({'error': '订单不存在'}, status=404)
    if order.status != 'pending':
        return Response({'error': '只能取消待付款订单'}, status=400)
    order.status = 'cancelled'
    order.save()
    return Response({'message': '订单已取消'})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def api_cart_count(request):
    """获取购物车商品数量"""
    cart, _ = Cart.objects.get_or_create(user=request.user)
    count = cart.items.aggregate(total=Count('id'))['total'] or 0
    return Response({'count': count})
