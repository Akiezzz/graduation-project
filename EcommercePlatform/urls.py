from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('product.urls')),
    path('user/', include('user.urls')),
    path('order/', include('order.urls')),
    path('store/', include('store.urls')),
    path('merchant/', include('merchant.urls')),
    path('', include('recommendation.urls')),
    path('manage/', include('admin_site.urls')),
    path('api/', include('api_urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
