"""Root URL configuration for product_service"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('modules.catalog.presentation.api.urls')),
]
