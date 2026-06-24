from django.urls import path

from . import views


app_name = 'catalog'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('about/', views.about, name='about'),
    path('contacts/', views.contacts, name='contacts'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('<str:product_type>/', views.product_list, name='product_type'),
]
