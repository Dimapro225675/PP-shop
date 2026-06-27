from decimal import Decimal
from unittest.mock import patch
from urllib.parse import urlencode

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.test import TestCase
from django.urls import reverse

from catalog.models import Product

from .cart import CART_SELECTED_SESSION_KEY, CART_SESSION_KEY
from .models import Order
from .payments import PaymentData, PaymentGatewayError


User = get_user_model()


CHECKOUT_DATA = {
    'fulfillment_method': Order.FulfillmentMethod.DELIVERY,
    'city': 'Москва',
    'street': 'Тверская',
    'house': '10',
    'entrance': '',
    'apartment': '',
    'comment': '',
}


def create_product(name, category, price):
    return Product.objects.create(
        category=category,
        name=name,
        price=Decimal(price),
        image='products/test.jpg',
        material='Фарфор',
        installation_type=Product.InstallationType.VANITY,
        manufacturer='Test',
        length_cm=Decimal('60.00'),
        width_cm=Decimal('45.00'),
        height_cm=Decimal('18.00'),
        color='Белый',
        shape='Овальная',
    )


class CartTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sink = create_product(
            'Раковина Nordic',
            Product.Category.SINK,
            '18000.00',
        )
        cls.faucet = create_product(
            'Кран Flow',
            Product.Category.FAUCET,
            '7000.00',
        )
        cls.user = User.objects.create_user(
            username='Customer',
            email='customer@example.com',
            password='StrongPass987!',
        )

    def test_empty_cart_displays_required_message(self):
        response = self.client.get(reverse('cart:detail'))
        self.assertContains(response, 'Товары не выбраны')

    def test_cart_accepts_quantity_without_stock_limit(self):
        add_url = reverse('cart:add', args=[self.sink.pk])
        self.client.post(add_url, {'quantity': 100})
        self.client.post(add_url, {'quantity': 50})

        self.assertEqual(
            self.client.session[CART_SESSION_KEY][str(self.sink.pk)],
            150,
        )

    @patch('cart.views.create_payment')
    def test_checkout_creates_payment_and_redirects_to_yookassa(self, create_payment_mock):
        create_payment_mock.return_value = PaymentData(
            payment_id='test-payment-1',
            status='pending',
            amount=Decimal('43500.00'),
            currency='RUB',
            metadata={},
            confirmation_url='https://yookassa.test/checkout/1',
        )
        self.client.post(reverse('cart:add', args=[self.sink.pk]), {'quantity': 2})
        self.client.post(reverse('cart:add', args=[self.faucet.pk]), {'quantity': 1})
        self.client.force_login(self.user)

        response = self.client.post(reverse('cart:checkout'), CHECKOUT_DATA)

        order = Order.objects.get()
        self.assertEqual(order.user, self.user)
        self.assertRedirects(
            response,
            'https://yookassa.test/checkout/1',
            fetch_redirect_response=False,
        )
        self.assertEqual(order.status, Order.Status.AWAITING_PAYMENT)
        self.assertEqual(order.payment_id, 'test-payment-1')
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.total_amount, Decimal('43500.00'))
        self.assertEqual(order.delivery_cost, Decimal('500.00'))
        self.assertEqual(order.fulfillment_method, Order.FulfillmentMethod.DELIVERY)
        self.assertEqual(order.delivery_city, 'Москва')
        self.assertEqual(order.delivery_street, 'Тверская')
        self.assertEqual(order.delivery_house, '10')
        self.assertNotIn(CART_SESSION_KEY, self.client.session)

    def test_cart_quantity_can_be_updated(self):
        self.client.post(reverse('cart:add', args=[self.sink.pk]), {'quantity': 2})
        self.client.post(reverse('cart:update', args=[self.sink.pk]), {'quantity': 25})
        self.assertEqual(
            self.client.session[CART_SESSION_KEY][str(self.sink.pk)],
            25,
        )

    def test_quantity_can_be_updated_with_ajax(self):
        self.client.post(reverse('cart:add', args=[self.sink.pk]), {'quantity': 2})

        response = self.client.post(
            reverse('cart:update', args=[self.sink.pk]),
            {'quantity': 4},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['item_total'], '72000,00 ₽')
        self.assertEqual(
            self.client.session[CART_SESSION_KEY][str(self.sink.pk)],
            4,
        )

    @patch('cart.views.create_payment')
    def test_checkout_only_selected_products_and_keeps_the_rest(self, create_payment_mock):
        create_payment_mock.return_value = PaymentData(
            payment_id='test-payment-2',
            status='pending',
            amount=Decimal('36500.00'),
            currency='RUB',
            metadata={},
            confirmation_url='https://yookassa.test/checkout/2',
        )
        self.client.post(reverse('cart:add', args=[self.sink.pk]), {'quantity': 2})
        self.client.post(reverse('cart:add', args=[self.faucet.pk]), {'quantity': 1})
        self.client.post(
            reverse('cart:select', args=[self.faucet.pk]),
            {'selected': '0'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.client.force_login(self.user)

        self.client.post(reverse('cart:checkout'), CHECKOUT_DATA)

        order = Order.objects.get()
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.get().product, self.sink)
        self.assertEqual(order.total_amount, Decimal('36500.00'))
        self.assertEqual(
            self.client.session[CART_SESSION_KEY],
            {str(self.faucet.pk): 1},
        )
        self.assertEqual(self.client.session[CART_SELECTED_SESSION_KEY], [])

    @patch('cart.views.create_payment')
    def test_gateway_error_keeps_cart_and_marks_order_failed(self, create_payment_mock):
        create_payment_mock.side_effect = PaymentGatewayError('ЮKassa недоступна')
        self.client.post(reverse('cart:add', args=[self.sink.pk]), {'quantity': 1})
        self.client.force_login(self.user)

        response = self.client.post(reverse('cart:checkout'), CHECKOUT_DATA, follow=True)

        order = Order.objects.get()
        self.assertEqual(order.status, Order.Status.PAYMENT_FAILED)
        self.assertContains(response, 'ЮKassa недоступна')
        self.assertIn(CART_SESSION_KEY, self.client.session)

    def test_checkout_requires_at_least_one_selected_product(self):
        self.client.post(reverse('cart:add', args=[self.sink.pk]), {'quantity': 1})
        self.client.post(
            reverse('cart:select', args=[self.sink.pk]),
            {'selected': '0'},
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('cart:checkout'), follow=True)

        self.assertContains(response, 'Выберите товары для оформления')
        self.assertFalse(Order.objects.exists())

    def test_checkout_page_displays_delivery_form_and_summary(self):
        self.client.post(reverse('cart:add', args=[self.sink.pk]), {'quantity': 1})
        self.client.force_login(self.user)

        response = self.client.get(reverse('cart:checkout'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Оформление заказа')
        self.assertContains(response, 'name="city"')
        self.assertContains(response, 'name="street"')
        self.assertContains(response, 'name="house"')
        self.assertContains(response, 'Доставка')
        self.assertContains(response, '500 ₽')
        self.assertContains(response, 'Самовывоз')

    @patch('cart.views.create_payment')
    def test_checkout_requires_delivery_address(self, create_payment_mock):
        self.client.post(reverse('cart:add', args=[self.sink.pk]), {'quantity': 1})
        self.client.force_login(self.user)

        response = self.client.post(reverse('cart:checkout'), {})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Обязательное поле')
        self.assertFalse(Order.objects.exists())
        create_payment_mock.assert_not_called()

    @patch('cart.views.create_payment')
    def test_checkout_pickup_does_not_require_delivery_address(self, create_payment_mock):
        create_payment_mock.return_value = PaymentData(
            payment_id='test-pickup-payment',
            status='pending',
            amount=Decimal('18000.00'),
            currency='RUB',
            metadata={},
            confirmation_url='https://yookassa.test/checkout/pickup',
        )
        self.client.post(reverse('cart:add', args=[self.sink.pk]), {'quantity': 1})
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('cart:checkout'),
            {
                'fulfillment_method': Order.FulfillmentMethod.PICKUP,
                'city': '',
                'street': '',
                'house': '',
                'entrance': '',
                'apartment': '',
                'comment': '',
            },
        )

        order = Order.objects.get()
        self.assertRedirects(
            response,
            'https://yookassa.test/checkout/pickup',
            fetch_redirect_response=False,
        )
        self.assertEqual(order.fulfillment_method, Order.FulfillmentMethod.PICKUP)
        self.assertEqual(order.delivery_cost, Decimal('0.00'))
        self.assertEqual(order.total_amount, Decimal('18000.00'))
        self.assertEqual(order.delivery_address_display, 'Самовывоз, Город: Белореченск; Улица: Ленина 55')

    @patch('cart.views.create_payment')
    def test_checkout_rejects_more_than_twenty_selected_items(self, create_payment_mock):
        self.client.post(reverse('cart:add', args=[self.sink.pk]), {'quantity': 21})
        self.client.force_login(self.user)

        response = self.client.post(reverse('cart:checkout'), follow=True)

        self.assertContains(response, 'За один заказ можно оформить не больше 20 товаров')
        self.assertFalse(Order.objects.exists())
        create_payment_mock.assert_not_called()
        self.assertEqual(
            self.client.session[CART_SESSION_KEY][str(self.sink.pk)],
            21,
        )

    def test_cart_product_links_to_detail_page(self):
        self.client.post(reverse('cart:add', args=[self.sink.pk]), {'quantity': 1})
        response = self.client.get(reverse('cart:detail'))
        self.assertContains(
            response,
            reverse('catalog:product_detail', args=[self.sink.pk]),
        )

    def test_anonymous_checkout_redirects_to_login_and_keeps_cart(self):
        self.client.post(reverse('cart:add', args=[self.sink.pk]), {'quantity': 1})
        response = self.client.post(reverse('cart:checkout'))

        expected_url = (
            f'{reverse("users:login")}?'
            f'{urlencode({"next": reverse("cart:checkout")})}'
        )
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)
        self.assertFalse(Order.objects.exists())
        self.assertEqual(
            self.client.session[CART_SESSION_KEY][str(self.sink.pk)],
            1,
        )

    def test_registration_keeps_anonymous_cart(self):
        self.client.post(reverse('cart:add', args=[self.sink.pk]), {'quantity': 2})
        response = self.client.post(
            reverse('users:register'),
            {
                'username': 'NewCustomer',
                'full_name': 'Петров Пётр Петрович',
                'phone': '8(999)111-22-33',
                'email': 'new@example.com',
                'password1': 'AnotherPass987!',
                'password2': 'AnotherPass987!',
                'next': reverse('cart:detail'),
            },
        )

        self.assertRedirects(response, reverse('home'))
        self.assertEqual(
            self.client.session[CART_SESSION_KEY][str(self.sink.pk)],
            2,
        )


class PaymentReturnTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='PaymentUser')
        cls.order = Order.objects.create(
            user=cls.user,
            status=Order.Status.AWAITING_PAYMENT,
            total_amount=Decimal('5000.00'),
            payment_id='payment-return-1',
            payment_status='pending',
        )

    @patch('cart.views.get_payment')
    def test_successful_payment_marks_order_paid(self, get_payment_mock):
        get_payment_mock.return_value = PaymentData(
            payment_id=self.order.payment_id,
            status='succeeded',
            amount=Decimal('5000.00'),
            currency='RUB',
            metadata={'order_id': str(self.order.pk)},
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('cart:payment_return', args=[self.order.pk])
        )

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertContains(response, 'Заказ оплачен')

    @patch('cart.views.get_payment')
    def test_mismatched_amount_does_not_mark_order_paid(self, get_payment_mock):
        get_payment_mock.return_value = PaymentData(
            payment_id=self.order.payment_id,
            status='succeeded',
            amount=Decimal('1.00'),
            currency='RUB',
            metadata={'order_id': str(self.order.pk)},
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('cart:payment_return', args=[self.order.pk])
        )

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.AWAITING_PAYMENT)
        self.assertContains(response, 'Сумма или валюта платежа не совпадает')

    def test_user_cannot_check_another_users_payment(self):
        another_user = User.objects.create_user(username='AnotherPaymentUser')
        self.client.force_login(another_user)
        response = self.client.get(
            reverse('cart:payment_return', args=[self.order.pk])
        )
        self.assertEqual(response.status_code, 404)


class OrderAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_superuser(
            username='OrderAdmin',
            email='admin@example.com',
            password='StrongPass987!',
        )

    def setUp(self):
        self.request = RequestFactory().get('/admin/cart/order/')
        self.request.user = self.admin_user
        self.order_admin = admin.site._registry[Order]

    def test_active_order_status_can_be_changed_to_delivery_statuses(self):
        order = Order.objects.create(user=self.admin_user, status=Order.Status.PAID)

        form_class = self.order_admin.get_form(self.request, order)
        available_statuses = {
            value for value, _label in form_class.base_fields['status'].choices
        }

        self.assertTrue(self.order_admin.has_change_permission(self.request, order))
        self.assertEqual(
            available_statuses,
            {
                Order.Status.PAID,
                Order.Status.SHIPPED,
                Order.Status.DELIVERED,
                Order.Status.CANCELLED,
            },
        )

    def test_finished_order_is_read_only(self):
        order = Order.objects.create(
            user=self.admin_user,
            status=Order.Status.DELIVERED,
        )

        self.assertFalse(self.order_admin.has_change_permission(self.request, order))
        self.assertIn(
            'status',
            self.order_admin.get_readonly_fields(self.request, order),
        )
