from django.urls import path

from . import views


app_name = 'users'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('favorites/<int:product_id>/toggle/', views.toggle_favorite, name='toggle_favorite'),
    path('orders/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path(
        'orders/history/<int:order_id>/hide/',
        views.hide_order_from_history,
        name='hide_order_history',
    ),
    path(
        'orders/history/clear/',
        views.clear_order_history,
        name='clear_order_history',
    ),
]
