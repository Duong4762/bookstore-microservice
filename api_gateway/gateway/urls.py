from django.urls import path
from . import views
from . import staff_views

urlpatterns = [
    path('api/chat/', views.chat_api, name='chat_api'),
    path('', views.home, name='home'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('products/<int:product_id>/add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('products/<int:product_id>/add-rating/', views.add_rating, name='add_rating'),
    # Backward compatible URLs
    path('books/<int:book_id>/', views.book_detail, name='book_detail'),
    path('books/<int:book_id>/add-to-cart/', views.add_to_cart, name='add_to_cart_legacy'),
    path('books/<int:book_id>/add-rating/', views.add_rating, name='add_rating_legacy'),
    
    path('account/login/', views.customer_account_login, name='customer_account_login'),
    path('customers/', views.customers_list, name='customers_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/logout/', views.customer_logout, name='customer_logout'),
    
    path('cart/', views.current_cart_view, name='current_cart_view'),
    path('cart/<int:customer_id>/', views.cart_view, name='cart_view'),
    
    path('orders/', views.orders_list, name='orders_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/create/', views.create_order, name='create_order'),

    path('staff/login/', staff_views.staff_login, name='staff_login'),
    path('staff/logout/', staff_views.staff_logout, name='staff_logout'),
    path('staff/products/', staff_views.staff_product_list, name='staff_product_list'),
    path('staff/products/new/', staff_views.staff_product_create, name='staff_product_create'),
    path('staff/products/<int:product_id>/edit/', staff_views.staff_product_edit, name='staff_product_edit'),
    path('staff/products/<int:product_id>/delete/', staff_views.staff_product_delete, name='staff_product_delete'),
]
