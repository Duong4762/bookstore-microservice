from django.urls import path
from .views import RecommendView, BestSellersView, InvalidateCacheView

urlpatterns = [
    path('recommend/', RecommendView.as_view(), name='recommend'),
    path('recommend/bestsellers/', BestSellersView.as_view(), name='recommend-bestsellers'),
    path('recommend/invalidate/', InvalidateCacheView.as_view(), name='recommend-invalidate'),
]
