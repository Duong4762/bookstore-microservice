"""Root URL configuration for AI Recommendation Service."""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    """Simple health check endpoint."""
    from ml.inference import ModelLoader
    loader = ModelLoader.instance()
    return JsonResponse({
        'status': 'ok',
        'service': 'recommender-ai',
        'ml_model_ready': loader.is_ready,
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/tracking/', include('apps.tracking.urls')),
    path('api/', include('apps.recommend.urls')),
    path('health/', health_check, name='health_check'),
]
