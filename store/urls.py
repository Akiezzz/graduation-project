"""
店铺路由配置
"""

from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # 店铺申请
    path('apply/', views.store_apply, name='apply'),
    path('apply/success/', views.store_apply_success, name='apply_success'),

    # 店铺管理（需要商家权限）
    path('<int:store_id>/dashboard/', views.store_dashboard, name='dashboard'),
    path('<int:store_id>/products/', views.store_product_manage, name='product_manage'),
    path('<int:store_id>/orders/', views.store_orders, name='orders'),
]
