from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cart.models import Order, OrderItem
from catalog.models import Product

from .models import Favorite, UserProfile
from .admin_forms import AdminUserChangeForm, AdminUserCreationForm


User = get_user_model()


class AuthenticationTests(TestCase):
    registration_data = {
        'username': 'NewUser123',
        'full_name': 'Иванов Иван Иванович',
        'phone': '8(999)123-45-67',
        'email': 'user@example.com',
        'password1': 'StrongPass987!',
        'password2': 'StrongPass987!',
    }

    def test_registration_creates_logged_in_regular_user(self):
        response = self.client.post(
            reverse('users:register'),
            self.registration_data,
        )

        user = User.objects.get(username='NewUser123')
        self.assertRedirects(response, reverse('catalog:product_list'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.profile.phone, '8(999)123-45-67')
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(
            username='Existing',
            email='USER@example.com',
            password='StrongPass987!',
        )

        response = self.client.post(
            reverse('users:register'),
            self.registration_data,
        )

        self.assertContains(response, 'Пользователь с таким Email уже существует')
        self.assertFalse(UserProfile.objects.exists())

    def test_login_and_post_logout(self):
        user = User.objects.create_user(
            username='Customer',
            password='StrongPass987!',
        )

        response = self.client.post(
            reverse('users:login'),
            {'username': 'Customer', 'password': 'StrongPass987!'},
        )
        self.assertRedirects(response, reverse('catalog:product_list'))
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

        response = self.client.post(reverse('users:logout'))
        self.assertRedirects(response, reverse('catalog:product_list'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_regular_user_cannot_open_admin(self):
        user = User.objects.create_user(
            username='Customer',
            password='StrongPass987!',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin:login'), response.url)

    def test_staff_user_can_open_admin(self):
        admin = User.objects.create_user(
            username='Manager',
            password='StrongPass987!',
            is_staff=True,
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 200)


class UserAdminFormTests(TestCase):
    def test_admin_creation_form_requires_profile_fields_and_sets_admin_role(self):
        form = AdminUserCreationForm({
            'username': 'StoreAdmin',
            'full_name': 'Иванов Иван Иванович',
            'phone': '8(999)555-44-33',
            'email': 'store-admin@example.com',
            'role': 'admin',
            'password1': 'StrongPass987!',
            'password2': 'StrongPass987!',
        })

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.profile.full_name, 'Иванов Иван Иванович')
        self.assertEqual(user.profile.phone, '8(999)555-44-33')

    def test_admin_change_form_updates_profile_and_removes_admin_role(self):
        user = User.objects.create_superuser(
            username='ExistingAdmin',
            email='old@example.com',
            password='StrongPass987!',
        )
        UserProfile.objects.create(
            user=user,
            full_name='Старое Имя',
            phone='8(999)111-22-33',
        )
        form = AdminUserChangeForm({
            'username': user.username,
            'full_name': 'Петров Пётр Петрович',
            'phone': '8(999)444-55-66',
            'email': 'new@example.com',
            'role': 'user',
            'is_active': True,
        }, instance=user)

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        user.refresh_from_db()
        user.profile.refresh_from_db()

        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.profile.full_name, 'Петров Пётр Петрович')
        self.assertEqual(user.profile.phone, '8(999)444-55-66')
        self.assertEqual(user.email, 'new@example.com')


class PersonalAccountTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='Customer',
            email='customer@example.com',
            password='StrongPass987!',
        )
        cls.profile = UserProfile.objects.create(
            user=cls.user,
            full_name='Иванов Иван Иванович',
            phone='8(999)123-45-67',
        )
        cls.product = Product.objects.create(
            category=Product.Category.SINK,
            name='Раковина Nordic',
            price=Decimal('18000.00'),
            image='products/test.jpg',
            material='Фарфор',
            installation_type=Product.InstallationType.VANITY,
            manufacturer='Nordic',
            length_cm=Decimal('60.00'),
            width_cm=Decimal('45.00'),
            height_cm=Decimal('18.00'),
            color='Белый',
            shape='Овальная',
        )

    def test_anonymous_profile_redirects_to_login_with_return_url(self):
        response = self.client.get(reverse('users:profile'))

        expected_url = f'{reverse("users:login")}?next={reverse("users:profile")}'
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)

    def test_favorite_can_be_added_and_removed(self):
        self.client.force_login(self.user)
        toggle_url = reverse('users:toggle_favorite', args=[self.product.pk])

        self.client.post(toggle_url, {'next': reverse('catalog:product_list')})
        self.assertTrue(
            Favorite.objects.filter(user=self.user, product=self.product).exists()
        )

        self.client.post(toggle_url, {'next': reverse('users:profile')})
        self.assertFalse(
            Favorite.objects.filter(user=self.user, product=self.product).exists()
        )

    def test_favorite_ajax_returns_current_state(self):
        self.client.force_login(self.user)
        toggle_url = reverse('users:toggle_favorite', args=[self.product.pk])

        added = self.client.post(
            toggle_url,
            {'next': reverse('catalog:product_list')},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        removed = self.client.post(
            toggle_url,
            {'next': reverse('catalog:product_list')},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(added.status_code, 200)
        self.assertEqual(added.json()['is_favorite'], True)
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(removed.json()['is_favorite'], False)

    def test_anonymous_favorite_ajax_returns_login_url(self):
        toggle_url = reverse('users:toggle_favorite', args=[self.product.pk])

        response = self.client.post(
            toggle_url,
            {'next': reverse('catalog:product_list')},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn(reverse('users:login'), response.json()['login_url'])

    def test_profile_displays_user_order_and_favorite(self):
        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal('36000.00'),
            delivery_date=date(2026, 7, 1),
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            unit_price=self.product.price,
            quantity=2,
        )
        Favorite.objects.create(user=self.user, product=self.product)
        self.client.force_login(self.user)

        response = self.client.get(reverse('users:profile'))

        self.assertContains(response, 'customer@example.com')
        self.assertContains(response, '8(999)123-45-67')
        self.assertNotContains(response, f'Заказ №{order.pk}')
        self.assertContains(response, f'{self.product.name} ×2')
        self.assertContains(response, '01.07.2026')
        self.assertContains(response, self.product.name)
        self.assertNotContains(response, '<dt>Роль</dt>', html=True)

    def test_registration_can_return_to_profile(self):
        response = self.client.post(
            reverse('users:register'),
            {
                'username': 'NewProfileUser',
                'full_name': 'Петров Пётр Петрович',
                'phone': '8(999)765-43-21',
                'email': 'profile@example.com',
                'password1': 'AnotherPass987!',
                'password2': 'AnotherPass987!',
                'next': reverse('users:profile'),
            },
        )

        self.assertRedirects(response, reverse('users:profile'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_user_can_cancel_active_order(self):
        order = Order.objects.create(
            user=self.user,
            status=Order.Status.NEW,
            total_amount=Decimal('18000.00'),
            delivery_date=timezone.localdate() + timedelta(days=5),
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('users:cancel_order', args=[order.pk]),
            follow=True,
        )

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertContains(response, f'Заказ №{order.pk} отменён')
        self.assertContains(response, 'Отменён')

    def test_user_cannot_cancel_another_users_order(self):
        another_user = User.objects.create_user(username='OrderOwner')
        order = Order.objects.create(
            user=another_user,
            delivery_date=timezone.localdate() + timedelta(days=5),
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('users:cancel_order', args=[order.pk])
        )

        self.assertEqual(response.status_code, 404)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.NEW)

    def test_favorite_card_links_to_product_detail(self):
        Favorite.objects.create(user=self.user, product=self.product)
        self.client.force_login(self.user)

        response = self.client.get(reverse('users:profile'))

        self.assertContains(response, 'class="favorite-card"')
        self.assertContains(
            response,
            reverse('catalog:product_detail', args=[self.product.pk]),
        )

    def test_expired_order_is_automatically_marked_delivered(self):
        order = Order.objects.create(
            user=self.user,
            status=Order.Status.NEW,
            total_amount=Decimal('18000.00'),
            delivery_date=timezone.localdate() - timedelta(days=1),
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('users:profile'))

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.DELIVERED)
        self.assertContains(response, 'Доставлен')
        self.assertContains(response, 'История заказов')

    def test_user_can_hide_one_delivered_order_only(self):
        delivered_order = Order.objects.create(
            user=self.user,
            status=Order.Status.DELIVERED,
            delivery_date=timezone.localdate(),
        )
        active_order = Order.objects.create(
            user=self.user,
            status=Order.Status.NEW,
            delivery_date=timezone.localdate() + timedelta(days=5),
        )
        another_user = User.objects.create_user(username='Another')
        another_order = Order.objects.create(
            user=another_user,
            status=Order.Status.DELIVERED,
            delivery_date=timezone.localdate(),
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('users:hide_order_history', args=[delivered_order.pk])
        )

        self.assertRedirects(response, reverse('users:profile'))
        delivered_order.refresh_from_db()
        active_order.refresh_from_db()
        another_order.refresh_from_db()
        self.assertTrue(delivered_order.hidden_from_history)
        self.assertFalse(active_order.hidden_from_history)
        self.assertFalse(another_order.hidden_from_history)
        self.assertEqual(
            self.client.post(
                reverse('users:hide_order_history', args=[active_order.pk])
            ).status_code,
            404,
        )

    def test_user_can_clear_all_history_without_hiding_active_orders(self):
        delivered_order = Order.objects.create(
            user=self.user,
            status=Order.Status.DELIVERED,
            delivery_date=timezone.localdate(),
        )
        cancelled_order = Order.objects.create(
            user=self.user,
            status=Order.Status.CANCELLED,
            delivery_date=timezone.localdate() + timedelta(days=2),
        )
        active_order = Order.objects.create(
            user=self.user,
            status=Order.Status.NEW,
            delivery_date=timezone.localdate() + timedelta(days=5),
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('users:clear_order_history'))

        self.assertRedirects(response, reverse('users:profile'))
        delivered_order.refresh_from_db()
        cancelled_order.refresh_from_db()
        active_order.refresh_from_db()
        self.assertTrue(delivered_order.hidden_from_history)
        self.assertTrue(cancelled_order.hidden_from_history)
        self.assertFalse(active_order.hidden_from_history)
