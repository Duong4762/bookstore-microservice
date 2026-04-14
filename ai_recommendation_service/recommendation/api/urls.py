from django.urls import path

from .views import (
    BestSellersView,
    InvalidateCacheView,
    RecommendGetView,
    RecommendPostCompatView,
    RetrainStatusView,
    RetrainView,
)

urlpatterns = [
    path('recommend', RecommendGetView.as_view(), name='recommend-get'),
    path('recommend/', RecommendPostCompatView.as_view(), name='recommend-post'),
    path('recommend/retrain', RetrainView.as_view(), name='recommend-retrain'),
    path('recommend/retrain/', RetrainView.as_view()),
    path('recommend/retrain/status', RetrainStatusView.as_view(), name='recommend-retrain-status'),
    path('recommend/bestsellers/', BestSellersView.as_view(), name='recommend-bestsellers'),
    path('recommend/invalidate/', InvalidateCacheView.as_view(), name='recommend-invalidate'),
]
