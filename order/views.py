from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from .models import Cart, CartItem, Order, OrderItem
from product.models import Product
from recommendation.models import UserBehavior
from recommendation.services import log_user_behavior


@login_required
def cart(request):
    cart_obj, _ = Cart.objects.get_or_create(user=request.user)
    items = cart_obj.items.select_related('product').all()
    total = sum(item.product.price * item.quantity for item in items)
    return render(request, 'order/cart.html', {'items': items, 'total': total})


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    cart_obj, _ = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(cart=cart_obj, product=product)
    if not created:
        item.quantity += 1
        item.save()
    log_user_behavior(request.user, product, UserBehavior.BEHAVIOR_CART)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        from django.db.models import Count
        cart_count = cart_obj.items.aggregate(total=Count('id'))['total'] or 0
        return JsonResponse({'status': 'ok', 'cart_count': cart_count})
    return redirect('cart')


@login_required
def remove_from_cart(request, item_id):
    CartItem.objects.filter(pk=item_id, cart__user=request.user).delete()
    return redirect('cart')


@login_required
def checkout(request):
    cart_obj, _ = Cart.objects.get_or_create(user=request.user)
    items = cart_obj.items.select_related('product').all()
    if not items:
        return redirect('cart')
    total = sum(item.product.price * item.quantity for item in items)
    if request.method == 'POST':
        address = request.POST.get('address', request.user.address)
        if not address:
            messages.error(request, '请填写收货地址')
            return render(request, 'order/checkout.html', {'items': items, 'total': total})
        remark = request.POST.get('remark', '')
        with transaction.atomic():
            product_ids = [item.product_id for item in items]
            products = Product.objects.select_for_update().filter(pk__in=product_ids, is_active=True)
            product_map = {p.id: p for p in products}

            for item in items:
                locked_product = product_map.get(item.product_id)
                if not locked_product:
                    messages.error(request, f'商品“{item.product.name}”不可购买')
                    return render(request, 'order/checkout.html', {'items': items, 'total': total})
                if locked_product.stock < item.quantity:
                    messages.error(request, f'商品“{locked_product.name}”库存不足')
                    return render(request, 'order/checkout.html', {'items': items, 'total': total})

            order_total = sum(product_map[item.product_id].price * item.quantity for item in items)
            order = Order.objects.create(
                user=request.user, address=address,
                total_price=order_total, remark=remark
            )
            for item in items:
                locked_product = product_map[item.product_id]
                OrderItem.objects.create(
                    order=order, product=locked_product,
                    quantity=item.quantity, price=locked_product.price
                )
                log_user_behavior(request.user, locked_product, UserBehavior.BEHAVIOR_ORDER)
                locked_product.stock -= item.quantity
                locked_product.sales += item.quantity
                locked_product.save(update_fields=['stock', 'sales'])
            cart_obj.items.all().delete()
        messages.success(request, '下单成功！')
        return redirect('order_detail', pk=order.pk)
    return render(request, 'order/checkout.html', {'items': items, 'total': total})


@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'order/list.html', {'orders': orders})


@login_required
def order_detail(request, pk):
    from django.db.models import Q
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product__store'),
        Q(pk=pk) & (Q(user=request.user) | Q(items__product__store__owner=request.user))
    )
    return render(request, 'order/detail.html', {'order': order})


@login_required
def pay_order(request, pk):
    if request.method != 'POST':
        return redirect('order_detail', pk=pk)
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if order.status != 'pending':
        messages.error(request, '当前订单状态不支持支付')
        return redirect('order_detail', pk=pk)
    order.status = 'paid'
    order.save(update_fields=['status'])
    messages.success(request, '支付成功，订单已更新为已付款')
    return redirect('order_detail', pk=pk)


@login_required
def cancel_order(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if order.status == 'pending':
        order.status = 'cancelled'
        order.save(update_fields=['status'])
        messages.success(request, '订单已取消')
    else:
        messages.error(request, '当前订单状态不支持取消')
    return redirect('order_detail', pk=pk)
