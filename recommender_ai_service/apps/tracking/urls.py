from django.urls import path
from .views import EventCollectorView, BatchEventCollectorView

urlpatterns = [
    path('event/', EventCollectorView.as_view(), name='tracking-event'),
    path('events/batch/', BatchEventCollectorView.as_view(), name='tracking-batch'),
]
