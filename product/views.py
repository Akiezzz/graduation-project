from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Product, Category, ProductReview
from recommendation.models import BrowseHistory, UserBehavior
from recommendation.services import log_user_behavior
from order.models import OrderItem


def index(request):
    categories = Category.objects.filter(parent=None)
    featured = Product.objects.filter(is_active=True).order_by('-sales')[:8]
    new_arrivals = Product.objects.filter(is_active=True).order_by('-created_at')[:8]
    return render(request, 'product/index.html', {
        'categories': categories,
        'featured': featured,
        'new_arrivals': new_arrivals,
    })


def product_list(request):
    products = Product.objects.filter(is_active=True)
    category_id = request.GET.get('category')
    q = request.GET.get('q', '')
    if category_id:
        products = products.filter(category_id=category_id)
    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(keywords__icontains=q)
        )
    categories = Category.objects.filter(parent=None)
    return render(request, 'product/list.html', {
        'products': products,
        'categories': categories,
        'q': q,
        'current_category': category_id,
    })


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    reviews = product.reviews.all().order_by('-created_at')
    if request.user.is_authenticated:
        BrowseHistory.objects.update_or_create(user=request.user, product=product)
        log_user_behavior(request.user, product, UserBehavior.BEHAVIOR_VIEW)
    return render(request, 'product/detail.html', {'product': product, 'reviews': reviews})


@login_required
def product_add(request):
    """商家添加商品"""
    from store.models import Store
    store_id = request.GET.get('store') or request.POST.get('store_id')
    store = get_object_or_404(Store, pk=store_id, owner=request.user)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        price = request.POST.get('price', '').strip()
        stock = request.POST.get('stock', 0)
        keywords = request.POST.get('keywords', '')
        description = request.POST.get('description', '')
        category_id = request.POST.get('category') or None
        image = request.FILES.get('image')

        if not name or not price:
            messages.error(request, '商品名称和价格为必填项')
        else:
            product = Product.objects.create(
                store=store,
                name=name,
                price=price,
                stock=stock,
                keywords=keywords,
                description=description,
                category_id=category_id,
                image=image,
                product_status='active',
                is_active=True,
            )
            messages.success(request, f'商品"{product.name}"已添加')
            return redirect(f'/store/{store.id}/products/')

    categories = Category.objects.all()
    return render(request, 'product/add.html', {'store': store, 'categories': categories})


@login_required
def product_edit(request, pk):
    """商家编辑商品"""
    product = get_object_or_404(Product, pk=pk)
    # 验证是否为店铺所有者
    if not product.store or product.store.owner != request.user:
        messages.error(request, '您没有权限编辑此商品')
        return redirect('/')

    if request.method == 'POST':
        product.name = request.POST.get('name', product.name).strip()
        product.price = request.POST.get('price', product.price)
        product.stock = request.POST.get('stock', product.stock)
        product.keywords = request.POST.get('keywords', '')
        product.description = request.POST.get('description', '')
        product.category_id = request.POST.get('category') or None
        if request.FILES.get('image'):
            product.image = request.FILES['image']
        product.save()
        messages.success(request, f'商品"{product.name}"已更新')
        return redirect(f'/store/{product.store.id}/products/')

    categories = Category.objects.all()
    return render(request, 'product/edit.html', {'product': product, 'categories': categories})


@login_required
def add_review(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        has_completed_order = OrderItem.objects.filter(
            order__user=request.user,
            order__status='completed',
            product=product,
        ).exists()
        if not has_completed_order:
            messages.error(request, '仅已完成订单用户可评价')
            return redirect('product_detail', pk=pk)
        rating = int(request.POST.get('rating', 5))
        content = request.POST.get('content', '')
        ProductReview.objects.update_or_create(
            product=product, user=request.user,
            defaults={'rating': rating, 'content': content}
        )
        log_user_behavior(request.user, product, UserBehavior.BEHAVIOR_REVIEW)
    return redirect('product_detail', pk=pk)
