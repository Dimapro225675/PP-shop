from django.urls import path

from . import views


app_name = 'cart'

urlpatterns = [
    path('', views.cart_detail, name='detail'),
    path('add/<int:product_id>/', views.add_to_cart, name='add'),
    path('update/<int:product_id>/', views.update_cart, name='update'),
    path('select/<int:product_id>/', views.select_cart_item, name='select'),
    path('remove/<int:product_id>/', views.remove_from_cart, name='remove'),
    path('checkout/', views.checkout, name='checkout'),
    path(
        'payment/return/<int:order_id>/',
        views.payment_return,
        name='payment_return',
    ),
]
