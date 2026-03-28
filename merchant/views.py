from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Merchant
from product.models import Product, Category
from order.models import Order, OrderItem


@login_required
def apply_merchant(request):
    if hasattr(request.user, 'merchant'):
        return redirect('merchant_dashboard')
    if request.method == 'POST':
        Merchant.objects.create(
            user=request.user,
            shop_name=request.POST['shop_name'],
            description=request.POST.get('description', ''),
        )
        messages.success(request, '申请已提交，等待审核')
        return redirect('merchant_dashboard')
    return render(request, 'merchant/apply.html')


@login_required
def merchant_dashboard(request):
    merchant = get_object_or_404(Merchant, user=request.user)
    products = Product.objects.filter(merchant=merchant).order_by('-created_at')
    orders = Order.objects.filter(items__product__merchant=merchant).distinct().order_by('-created_at')[:10]
    return render(request, 'merchant/dashboard.html', {
        'merchant': merchant,
        'products': products,
        'orders': orders,
    })


@login_required
def product_add(request):
    merchant = get_object_or_404(Merchant, user=request.user, is_approved=True)
    categories = Category.objects.filter(parent=None)
    if request.method == 'POST':
        product = Product.objects.create(
            merchant=merchant,
            name=request.POST['name'],
            keywords=request.POST.get('keywords', ''),
            description=request.POST.get('description', ''),
            price=request.POST['price'],
            stock=request.POST.get('stock', 0),
            category_id=request.POST['category'],
        )
        if request.FILES.get('image'):
            product.image = request.FILES['image']
            product.save()
        messages.success(request, '商品已添加')
        return redirect('merchant_dashboard')
    return render(request, 'merchant/product_form.html', {'categories': categories})


@login_required
def product_edit(request, pk):
    merchant = get_object_or_404(Merchant, user=request.user)
    product = get_object_or_404(Product, pk=pk, merchant=merchant)
    categories = Category.objects.filter(parent=None)
    if request.method == 'POST':
        product.name = request.POST['name']
        product.keywords = request.POST.get('keywords', '')
        product.description = request.POST.get('description', '')
        product.price = request.POST['price']
        product.stock = request.POST.get('stock', 0)
        product.category_id = request.POST['category']
        product.is_active = 'is_active' in request.POST
        if request.FILES.get('image'):
            product.image = request.FILES['image']
        product.save()
        messages.success(request, '商品已更新')
        return redirect('merchant_dashboard')
    return render(request, 'merchant/product_form.html', {'product': product, 'categories': categories})
