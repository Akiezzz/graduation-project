from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from store.models import Store
from order.models import Order
from user.models import User
from product.models import Product


@staff_member_required
def admin_dashboard(request):
    return render(request, 'admin_site/dashboard.html', {
        'user_count': User.objects.count(),
        'product_count': Product.objects.count(),
        'order_count': Order.objects.count(),
        'store_count': Store.objects.filter(status='active').count(),
    })


@staff_member_required
def store_approval(request):
    """店铺申请审核"""
    if request.method == 'POST':
        store_id = request.POST.get('store_id')
        action = request.POST.get('action')
        store = get_object_or_404(Store, pk=store_id)

        if action == 'approve':
            store.status = 'active'
            store.reviewed_by = request.user
            store.reviewed_at = timezone.now()
            store.save()
            messages.success(request, f'店铺「{store.name}」已审核通过')
        elif action == 'reject':
            store.status = 'rejected'
            store.reviewed_by = request.user
            store.reviewed_at = timezone.now()
            store.save()
            messages.success(request, f'已拒绝店铺「{store.name}」的申请')
        elif action == 'disable':
            store.status = 'disabled'
            store.save()
            messages.success(request, f'店铺「{store.name}」已禁用')
        elif action == 'enable':
            store.status = 'active'
            store.save()
            messages.success(request, f'店铺「{store.name}」已启用')
        return redirect('store_approval')

    pending_stores = Store.objects.filter(status='pending').select_related('owner')
    active_stores = Store.objects.filter(status='active').select_related('owner')
    return render(request, 'admin_site/store_approval.html', {
        'pending_stores': pending_stores,
        'active_stores': active_stores,
    })


@staff_member_required
def product_violation(request):
    """商品违规下架"""
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        action = request.POST.get('action')
        product = get_object_or_404(Product, pk=product_id)

        if action == 'violate':
            product.product_status = 'violated'
            product.is_active = False
            product.save()
            messages.success(request, f'商品「{product.name}」已强制下架')
        elif action == 'restore':
            product.product_status = 'active'
            product.is_active = True
            product.save()
            messages.success(request, f'商品「{product.name}」已恢复上架')
        return redirect('product_violation')

    q = request.GET.get('q', '')
    products = Product.objects.select_related('store').order_by('-created_at')
    if q:
        products = products.filter(name__icontains=q)
    return render(request, 'admin_site/product_violation.html', {
        'products': products,
        'q': q,
    })
