from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from catalog.models import Product
from cart.models import Order

from .forms import LoginForm, RegisterForm
from .models import Favorite


HISTORY_ORDER_STATUSES = (
    Order.Status.DELIVERED,
    Order.Status.CANCELLED,
    Order.Status.PAYMENT_FAILED,
)


def _safe_next_url(request):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return reverse('catalog:product_list')


class UserLoginView(LoginView):
    authentication_form = LoginForm
    template_name = 'users/login.html'
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    http_method_names = ('post',)


def register(request):
    if request.user.is_authenticated:
        return redirect(_safe_next_url(request))

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            user = form.save()
        login(request, user)
        messages.success(request, 'Регистрация завершена')
        return redirect(_safe_next_url(request))

    return render(
        request,
        'users/register.html',
        {'form': form, 'next': request.POST.get('next') or request.GET.get('next')},
    )


@login_required
def profile(request):
    request.user.orders.filter(
        delivery_date__lte=timezone.localdate(),
        status__in=(Order.Status.NEW, Order.Status.PAID, Order.Status.SHIPPED),
    ).update(status=Order.Status.DELIVERED)

    orders = request.user.orders.prefetch_related('items__product')
    return render(
        request,
        'users/profile.html',
        {
            'user_profile': getattr(request.user, 'profile', None),
            'active_orders': orders.exclude(status__in=HISTORY_ORDER_STATUSES),
            'order_history': orders.filter(
                status__in=HISTORY_ORDER_STATUSES,
                hidden_from_history=False,
            ),
            'favorites': request.user.favorites.select_related('product'),
        },
    )


@require_POST
def toggle_favorite(request, product_id):
    redirect_target = _safe_next_url(request)
    if not request.user.is_authenticated:
        login_url = reverse('users:login')
        redirect_url = f'{login_url}?{urlencode({"next": redirect_target})}'
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'login_url': redirect_url}, status=401)
        return redirect(redirect_url)

    product = get_object_or_404(Product, pk=product_id)
    favorite, created = Favorite.objects.get_or_create(
        user=request.user,
        product=product,
    )
    if created:
        message = f'«{product.name}» добавлен в избранное'
    else:
        favorite.delete()
        message = f'«{product.name}» удалён из избранного'

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'is_favorite': created, 'message': message})

    messages.success(request, message)
    return redirect(redirect_target)


@login_required
@require_POST
def cancel_order(request, order_id):
    order = get_object_or_404(
        Order,
        pk=order_id,
        user=request.user,
    )
    if order.status in HISTORY_ORDER_STATUSES:
        messages.error(request, 'Этот заказ уже нельзя отменить')
        return redirect('users:profile')

    if order.delivery_date <= timezone.localdate():
        order.status = Order.Status.DELIVERED
        order.save(update_fields=('status',))
        messages.error(request, 'Доставленный заказ нельзя отменить')
        return redirect('users:profile')

    order.status = Order.Status.CANCELLED
    order.hidden_from_history = False
    order.save(update_fields=('status', 'hidden_from_history'))
    messages.success(request, f'Заказ №{order.pk} отменён')
    return redirect('users:profile')


@login_required
@require_POST
def hide_order_from_history(request, order_id):
    order = get_object_or_404(
        Order,
        pk=order_id,
        user=request.user,
        status__in=HISTORY_ORDER_STATUSES,
    )
    if not order.hidden_from_history:
        order.hidden_from_history = True
        order.save(update_fields=('hidden_from_history',))
        messages.success(request, f'Заказ №{order.pk} удалён из истории')
    return redirect('users:profile')


@login_required
@require_POST
def clear_order_history(request):
    updated = request.user.orders.filter(
        status__in=HISTORY_ORDER_STATUSES,
        hidden_from_history=False,
    ).update(hidden_from_history=True)
    if updated:
        messages.success(request, 'История заказов очищена')
    return redirect('users:profile')
