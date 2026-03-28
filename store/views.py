"""
商家店铺视图
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Store
from .decorators import store_owner_required
from product.models import Product


@login_required
def store_apply(request):
    """申请开店"""
    # 检查用户是否已经有店铺
    if hasattr(request.user, 'owned_store'):
        messages.info(request, '您已经拥有店铺，无需重复申请')
        return redirect(f'/store/{request.user.owned_store.id}/dashboard/')

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        contact_person = request.POST.get('contact_person')
        contact_phone = request.POST.get('contact_phone')
        license_number = request.POST.get('license_number')

        # 简单验证
        if not all([name, contact_person, contact_phone, license_number]):
            messages.error(request, '请填写所有必填字段')
            return render(request, 'store/apply.html')

        # 检查营业执照号是否已被使用
        if Store.objects.filter(license_number=license_number).exists():
            messages.error(request, '该营业执照号已被使用')
            return render(request, 'store/apply.html')

        # 创建店铺（待审核状态）
        store = Store.objects.create(
            name=name,
            description=description,
            contact_person=contact_person,
            contact_phone=contact_phone,
            license_number=license_number,
            owner=request.user,
            status='pending'
        )

        messages.success(request, '店铺申请已提交，请等待管理员审核')
        return redirect('/store/apply/success/')

    return render(request, 'store/apply.html')


@login_required
def store_apply_success(request):
    """申请成功页面"""
    return render(request, 'store/apply_success.html')


@login_required
@store_owner_required()
def store_dashboard(request, store):
    """商家店铺首页"""
    # 获取店铺商品统计
    products = store.products.all()
    total_products = products.count()
    active_products = products.filter(product_status='active').count()

    # 获取店铺订单统计
    from order.models import Order, OrderItem
    order_items = OrderItem.objects.filter(product__in=products)
    total_orders = Order.objects.filter(items__product__in=products).distinct().count()

    context = {
        'store': store,
        'total_products': total_products,
        'active_products': active_products,
        'total_orders': total_orders,
    }
    return render(request, 'store/dashboard.html', context)


@login_required
@store_owner_required()
def store_product_manage(request, store):
    """商家管理自己店铺的商品"""
    products = store.products.all()

    # 处理商品上架/下架操作
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        action = request.POST.get('action')

        if product_id and action:
            product = get_object_or_404(Product, pk=product_id)

            # 验证商品是否属于此店铺
            if product.store != store:
                messages.error(request, '您没有权限操作此商品')
                return redirect(f'/store/{store.id}/products/')

            if action == 'active':
                product.product_status = 'active'
                product.is_active = True
                product.save()
                messages.success(request, f'商品"{product.name}"已上架')
            elif action == 'inactive':
                product.product_status = 'inactive'
                product.is_active = False
                product.save()
                messages.success(request, f'商品"{product.name}"已下架')

        return redirect(f'/store/{store.id}/products/')

    context = {
        'store': store,
        'products': products,
    }
    return render(request, 'store/products.html', context)


@login_required
@store_owner_required()
def store_orders(request, store):
    """商家查看自己店铺的订单"""
    from order.models import Order, OrderItem

    # 获取包含本店铺商品的订单
    order_items = OrderItem.objects.filter(product__in=store.products.all())
    orders = Order.objects.filter(items__in=order_items).distinct().order_by('-created_at')

    context = {
        'store': store,
        'orders': orders,
    }
    return render(request, 'store/orders.html', context)
