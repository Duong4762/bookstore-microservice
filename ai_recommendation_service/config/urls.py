from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    from recommendation.services.inference import RecommendEngine

    eng = RecommendEngine.instance()
    return JsonResponse(
        {
            'status': 'ok',
            'service': 'ai-recommendation-gnn',
            'ml_ready': eng.is_ready,
            'load_error': eng.load_error,
        }
    )


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/tracking/', include('tracking.urls')),
    path('api/', include('recommendation.api.urls')),
    path('health/', health_check, name='health'),
]
