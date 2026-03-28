from django.urls import path
from product.api_views import CategoryListView, ProductListView, ProductDetailView, product_reviews
from order.api_views import api_cart, api_cart_add, api_cart_remove, api_cart_count, api_orders, api_order_detail, api_order_pay, api_order_cancel
from user.api_views import api_register, api_login, api_logout, UserProfileView
from merchant.api_views import api_merchant_products, api_merchant_product_detail, api_merchant_orders, api_merchant_profile
from admin_site.api_views import api_admin_stats, api_admin_users, api_admin_merchants, api_admin_orders
from recommendation.api_views import api_recommendations

urlpatterns = [
    # 用户端
    path('auth/register/', api_register, name='api_register'),
    path('auth/login/', api_login, name='api_login'),
    path('auth/logout/', api_logout, name='api_logout'),
    path('user/profile/', UserProfileView.as_view(), name='api_profile'),

    # 商品
    path('categories/', CategoryListView.as_view(), name='api_categories'),
    path('products/', ProductListView.as_view(), name='api_products'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='api_product_detail'),
    path('products/<int:pk>/reviews/', product_reviews, name='api_product_reviews'),
    path('recommendations/', api_recommendations, name='api_recommendations'),

    # 购物车 & 订单
    path('cart/', api_cart, name='api_cart'),
    path('cart/add/', api_cart_add, name='api_cart_add'),
    path('cart/<int:item_id>/', api_cart_remove, name='api_cart_remove'),
    path('cart/count/', api_cart_count, name='api_cart_count'),
    path('orders/', api_orders, name='api_orders'),
    path('orders/<int:pk>/', api_order_detail, name='api_order_detail'),
    path('orders/<int:pk>/pay/', api_order_pay, name='api_order_pay'),
    path('orders/<int:pk>/cancel/', api_order_cancel, name='api_order_cancel'),

    # 商家端
    path('merchant/', api_merchant_profile, name='api_merchant_profile'),
    path('merchant/products/', api_merchant_products, name='api_merchant_products'),
    path('merchant/products/<int:pk>/', api_merchant_product_detail, name='api_merchant_product_detail'),
    path('merchant/orders/', api_merchant_orders, name='api_merchant_orders'),

    # 管理员端
    path('admin/stats/', api_admin_stats, name='api_admin_stats'),
    path('admin/users/', api_admin_users, name='api_admin_users'),
    path('admin/merchants/', api_admin_merchants, name='api_admin_merchants'),
    path('admin/orders/', api_admin_orders, name='api_admin_orders'),
]
