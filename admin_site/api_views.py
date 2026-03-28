from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from user.models import User
from user.serializers import UserSerializer
from merchant.models import Merchant
from merchant.serializers import MerchantSerializer
from product.models import Product
from order.models import Order


class IsStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff


@api_view(['GET'])
@permission_classes([IsStaff])
def api_admin_stats(request):
    return Response({
        'users': User.objects.count(),
        'products': Product.objects.count(),
        'orders': Order.objects.count(),
        'merchants': Merchant.objects.count(),
        'pending_merchants': Merchant.objects.filter(is_approved=False).count(),
    })


@api_view(['GET'])
@permission_classes([IsStaff])
def api_admin_users(request):
    users = User.objects.all().order_by('-date_joined')
    return Response(UserSerializer(users, many=True).data)


@api_view(['GET', 'POST'])
@permission_classes([IsStaff])
def api_admin_merchants(request):
    if request.method == 'GET':
        approved = request.query_params.get('approved')
        qs = Merchant.objects.all()
        if approved is not None:
            qs = qs.filter(is_approved=approved.lower() == 'true')
        return Response(MerchantSerializer(qs, many=True).data)
    # POST: approve or reject
    merchant_id = request.data.get('merchant_id')
    action = request.data.get('action')
    try:
        merchant = Merchant.objects.get(pk=merchant_id)
    except Merchant.DoesNotExist:
        return Response({'error': '商家不存在'}, status=404)
    if action == 'approve':
        merchant.is_approved = True
        merchant.save()
        return Response({'message': f'{merchant.shop_name} 已审核通过'})
    elif action == 'reject':
        merchant.delete()
        return Response({'message': '已拒绝申请'})
    return Response({'error': '无效操作'}, status=400)


@api_view(['GET'])
@permission_classes([IsStaff])
def api_admin_orders(request):
    from order.models import Order
    from order.serializers import OrderSerializer
    orders = Order.objects.all().order_by('-created_at')
    return Response(OrderSerializer(orders, many=True).data)
