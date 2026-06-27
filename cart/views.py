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
from .forms import CheckoutForm
from .models import Order, OrderItem
from .payments import PaymentGatewayError, create_payment, get_payment


MAX_CHECKOUT_QUANTITY = 20
DELIVERY_COST = Decimal('500.00')
PICKUP_COST = Decimal('0.00')


def _is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def _money(value):
    return f'{value:.2f}'.replace('.', ',') + ' ₽'


def _cart_payload(cart, item_total=None):
    selected_quantities = cart.selected_quantities()
    payload = {
        'selected_total': _money(cart.selected_total()),
        'selected_count': sum(selected_quantities.values()),
        'has_selected': bool(selected_quantities),
    }
    if item_total is not None:
        payload['item_total'] = _money(item_total)
    return payload


def _cart_action_payload(cart, product, in_cart, message):
    return {
        **_cart_payload(cart),
        'product_id': product.pk,
        'in_cart': in_cart,
        'message': message,
    }


def cart_detail(request):
    cart = Cart(request)
    cart_items = cart.items()
    selected_quantities = cart.selected_quantities()
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
            'selected_count': sum(selected_quantities.values()),
            'max_checkout_quantity': MAX_CHECKOUT_QUANTITY,
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
    cart = Cart(request)
    try:
        cart.add(product, _quantity_from_request(request))
    except ValueError as error:
        if _is_ajax(request):
            return JsonResponse({'error': str(error)}, status=400)
        messages.error(request, str(error))
    else:
        message = f'«{product.name}» добавлен в корзину'
        if _is_ajax(request):
            return JsonResponse(_cart_action_payload(cart, product, True, message))
        messages.success(request, message)
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
    product = get_object_or_404(Product, pk=product_id)
    cart = Cart(request)
    cart.remove(product_id)
    message = f'«{product.name}» удалён из корзины'
    if _is_ajax(request):
        return JsonResponse({
            **_cart_action_payload(cart, product, False, message),
            'cart_empty': not bool(cart.quantities),
        })
    return redirect('cart:detail')


def _selected_checkout_items(cart):
    selected_quantities = cart.selected_quantities()
    if not selected_quantities:
        return None, 'Выберите товары для оформления'

    selected_quantity = sum(selected_quantities.values())
    if selected_quantity > MAX_CHECKOUT_QUANTITY:
        return None, f'За один заказ можно оформить не больше {MAX_CHECKOUT_QUANTITY} товаров'

    product_ids = [int(product_id) for product_id in selected_quantities]
    products = {
        product.pk: product
        for product in Product.objects.filter(pk__in=product_ids)
    }

    items = []
    subtotal = Decimal('0.00')
    for raw_product_id, quantity in selected_quantities.items():
        product = products.get(int(raw_product_id))
        if product is None:
            return None, 'Один из выбранных товаров больше недоступен'
        item_total = product.price * quantity
        subtotal += item_total
        items.append({
            'product': product,
            'quantity': quantity,
            'total_price': item_total,
        })

    return {
        'items': items,
        'selected_quantities': selected_quantities,
        'subtotal': subtotal,
        'delivery_cost': DELIVERY_COST,
        'total': subtotal + DELIVERY_COST,
    }, ''


def _delivery_cost_for_method(fulfillment_method):
    if fulfillment_method == Order.FulfillmentMethod.PICKUP:
        return PICKUP_COST
    return DELIVERY_COST


def _checkout_context(form, checkout_data):
    delivery_cost = _delivery_cost_for_method(
        form.data.get('fulfillment_method') if form.is_bound else form.initial.get('fulfillment_method')
    )
    return {
        'form': form,
        **checkout_data,
        'delivery_cost': delivery_cost,
        'total': checkout_data['subtotal'] + delivery_cost,
    }


def checkout(request):
    cart = Cart(request)
    checkout_data, error_message = _selected_checkout_items(cart)
    if error_message:
        messages.error(request, error_message)
        return redirect('cart:detail')

    if not request.user.is_authenticated:
        login_url = reverse('users:login')
        checkout_url = reverse('cart:checkout')
        return redirect(f'{login_url}?{urlencode({"next": checkout_url})}')

    form = CheckoutForm(request.POST if request.method == 'POST' else None)
    if request.method != 'POST':
        return render(
            request,
            'cart/checkout.html',
            _checkout_context(form, checkout_data),
        )

    if not form.is_valid():
        return render(
            request,
            'cart/checkout.html',
            _checkout_context(form, checkout_data),
        )

    if request.session.session_key is None:
        request.session.save()

    fulfillment_method = form.cleaned_data['fulfillment_method']
    delivery_cost = _delivery_cost_for_method(fulfillment_method)
    total_amount = checkout_data['subtotal'] + delivery_cost
    is_pickup = fulfillment_method == Order.FulfillmentMethod.PICKUP

    with transaction.atomic():
        order = Order.objects.create(
            user=request.user,
            session_key=request.session.session_key,
            total_amount=total_amount,
            delivery_cost=delivery_cost,
            fulfillment_method=fulfillment_method,
            delivery_city='' if is_pickup else form.cleaned_data['city'],
            delivery_street='' if is_pickup else form.cleaned_data['street'],
            delivery_house='' if is_pickup else form.cleaned_data['house'],
            delivery_apartment='' if is_pickup else form.cleaned_data['apartment'],
            delivery_entrance='' if is_pickup else form.cleaned_data['entrance'],
            delivery_comment=form.cleaned_data['comment'],
            status=Order.Status.AWAITING_PAYMENT,
        )
        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                product=item['product'],
                product_name=item['product'].name,
                unit_price=item['product'].price,
                quantity=item['quantity'],
            )
            for item in checkout_data['items']
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
    cart.clear_products(checkout_data['selected_quantities'])
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
