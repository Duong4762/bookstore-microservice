from django.urls import path

from .views import BatchEventCollectorView, EventCollectorView

urlpatterns = [
    path('event/', EventCollectorView.as_view(), name='tracking-event'),
    path('events/batch/', BatchEventCollectorView.as_view(), name='tracking-batch'),
]
