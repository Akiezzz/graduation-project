from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('stores/', views.store_approval, name='store_approval'),
    path('products/', views.product_violation, name='product_violation'),
]
