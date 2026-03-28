from django.urls import path
from . import views

urlpatterns = [
    path('apply/', views.apply_merchant, name='apply_merchant'),
    path('dashboard/', views.merchant_dashboard, name='merchant_dashboard'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
]
