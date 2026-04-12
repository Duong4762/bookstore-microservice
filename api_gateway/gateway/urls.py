from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('books/<int:book_id>/', views.book_detail, name='book_detail'),
    path('books/<int:book_id>/add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('books/<int:book_id>/add-rating/', views.add_rating, name='add_rating'),
    
    path('customers/', views.customers_list, name='customers_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    
    path('cart/<int:customer_id>/', views.cart_view, name='cart_view'),
    
    path('orders/', views.orders_list, name='orders_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/create/', views.create_order, name='create_order'),
]
