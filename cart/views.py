from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from catalog.models import Product

from .cart import Cart
from .models import Order, OrderItem
from .payments import PaymentGatewayError, create_payment, get_payment


def _is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def _money(value):
    return f'{value:.2f}'.replace('.', ',') + ' ₽'


def _cart_payload(cart, item_total=None):
    payload = {
        'selected_total': _money(cart.selected_total()),
        'selected_count': len(cart.selected_ids),
        'has_selected': bool(cart.selected_ids),
    }
    if item_total is not None:
        payload['item_total'] = _money(item_total)
    return payload


def cart_detail(request):
    cart = Cart(request)
    cart_items = cart.items()
    return render(
        request,
        'cart/detail.html',
        {
            'cart_items': cart_items,
            'selected_total': sum(
                (
                    item['total_price']
                    for item in cart_items
                    if item['selected']
                ),
                start=Decimal('0.00'),
            ),
            'selected_count': len(cart.selected_ids),
        },
    )


def _quantity_from_request(request, default=1):
    try:
        return int(request.POST.get('quantity', default))
    except (TypeError, ValueError):
        return 0


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    try:
        Cart(request).add(product, _quantity_from_request(request))
    except ValueError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f'«{product.name}» добавлен в корзину')
    return redirect('cart:detail')


@require_POST
def update_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    cart = Cart(request)
    quantity = _quantity_from_request(request, default=0)
    try:
        cart.update(product, quantity)
    except ValueError as error:
        if _is_ajax(request):
            return JsonResponse({'error': str(error)}, status=400)
        messages.error(request, str(error))
    else:
        if _is_ajax(request):
            return JsonResponse(
                _cart_payload(cart, product.price * quantity)
            )
        messages.success(request, 'Количество обновлено')
    return redirect('cart:detail')


@require_POST
def select_cart_item(request, product_id):
    cart = Cart(request)
    selected = request.POST.get('selected') in ('1', 'true', 'on')
    try:
        cart.set_selected(product_id, selected)
    except KeyError:
        return JsonResponse({'error': 'Товар отсутствует в корзине'}, status=404)
    return JsonResponse(_cart_payload(cart))


@require_POST
def remove_from_cart(request, product_id):
    Cart(request).remove(product_id)
    return redirect('cart:detail')


@require_POST
def checkout(request):
    cart = Cart(request)
    selected_quantities = cart.selected_quantities()
    if not selected_quantities:
        messages.error(request, 'Выберите товары для оформления')
        return redirect('cart:detail')
    if not request.user.is_authenticated:
        login_url = reverse('users:login')
        cart_url = reverse('cart:detail')
        return redirect(f'{login_url}?{urlencode({"next": cart_url})}')

    if request.session.session_key is None:
        request.session.save()

    with transaction.atomic():
        product_ids = [int(product_id) for product_id in selected_quantities]
        products = {
            product.pk: product
            for product in Product.objects.filter(pk__in=product_ids)
        }

        order_rows = []
        total_amount = Decimal('0.00')
        for raw_product_id, quantity in selected_quantities.items():
            product = products.get(int(raw_product_id))
            if product is None:
                messages.error(request, 'Один из выбранных товаров больше недоступен')
                return redirect('cart:detail')
            total_amount += product.price * quantity
            order_rows.append((product, quantity))

        order = Order.objects.create(
            user=request.user,
            session_key=request.session.session_key,
            total_amount=total_amount,
            status=Order.Status.AWAITING_PAYMENT,
        )
        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                product=product,
                product_name=product.name,
                unit_price=product.price,
                quantity=quantity,
            )
            for product, quantity in order_rows
        ])

    return_url = request.build_absolute_uri(
        reverse('cart:payment_return', args=[order.pk])
    )
    try:
        payment = create_payment(order, return_url)
        if not payment.confirmation_url:
            raise PaymentGatewayError('ЮKassa не вернула ссылку на оплату')
    except PaymentGatewayError as error:
        order.status = Order.Status.PAYMENT_FAILED
        order.payment_status = 'creation_failed'
        order.save(update_fields=('status', 'payment_status'))
        messages.error(request, str(error))
        return redirect('cart:detail')

    order.payment_id = payment.payment_id
    order.payment_status = payment.status
    order.payment_confirmation_url = payment.confirmation_url
    order.save(update_fields=(
        'payment_id',
        'payment_status',
        'payment_confirmation_url',
    ))
    cart.clear_products(selected_quantities)
    return redirect(payment.confirmation_url)


def _sync_order_payment(order):
    if not order.payment_id:
        raise PaymentGatewayError('У заказа отсутствует платёж ЮKassa')

    payment = get_payment(order.payment_id)
    if payment.payment_id != order.payment_id:
        raise PaymentGatewayError('ЮKassa вернула другой идентификатор платежа')
    if payment.amount != order.total_amount or payment.currency != 'RUB':
        raise PaymentGatewayError('Сумма или валюта платежа не совпадает с заказом')
    if str(payment.metadata.get('order_id')) != str(order.pk):
        raise PaymentGatewayError('Платёж не принадлежит этому заказу')

    order.payment_status = payment.status
    if payment.status == 'succeeded':
        order.status = Order.Status.PAID
    elif payment.status == 'canceled':
        order.status = Order.Status.CANCELLED
    else:
        order.status = Order.Status.AWAITING_PAYMENT
    order.save(update_fields=('payment_status', 'status'))
    return payment


@login_required
@require_GET
def payment_return(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    error_message = ''
    try:
        _sync_order_payment(order)
    except PaymentGatewayError as error:
        error_message = str(error)

    return render(
        request,
        'cart/payment_result.html',
        {
            'order': order,
            'error_message': error_message,
        },
    )
