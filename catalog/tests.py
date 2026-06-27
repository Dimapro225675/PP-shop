from decimal import Decimal
from io import StringIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from cart.models import Order
from users.models import ProductRecommendation
from users.models import UserProfile

from .models import Product, ProductImage


def product_data(**overrides):
    data = {
        'category': Product.Category.SINK,
        'name': 'Раковина Nordic',
        'price': Decimal('18990.00'),
        'image': 'products/test.jpg',
        'material': 'Фарфор',
        'installation_type': Product.InstallationType.VANITY,
        'manufacturer': 'Nordic',
        'length_cm': Decimal('60.00'),
        'width_cm': Decimal('45.00'),
        'height_cm': Decimal('18.00'),
        'color': 'Белый',
        'shape': 'Овальная',
    }
    data.update(overrides)
    return data


class ProductCatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sink = Product.objects.create(**product_data())
        cls.bathtub = Product.objects.create(**product_data(
            category=Product.Category.BATHTUB,
            name='Ванна Forma',
            price=Decimal('74990.00'),
            material='Акрил',
            installation_type=Product.InstallationType.FLOOR_STANDING,
            manufacturer='Forma',
            length_cm=Decimal('170.00'),
            width_cm=Decimal('75.00'),
            height_cm=Decimal('58.00'),
            shape='Прямоугольная',
        ))

    def test_catalog_displays_fixed_categories(self):
        response = self.client.get(reverse('catalog:product_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Раковины')
        self.assertContains(response, 'Ванны')

    def test_category_page_displays_only_selected_category(self):
        response = self.client.get(
            reverse('catalog:product_type', args=[Product.Category.SINK])
        )

        self.assertContains(response, self.sink.name)
        self.assertContains(response, self.sink.manufacturer)
        self.assertNotContains(response, self.bathtub.name)

    def test_catalog_paginates_by_fifteen_products(self):
        Product.objects.bulk_create([
            Product(**product_data(name=f'Р Р°РєРѕРІРёРЅР° Page {number}'))
            for number in range(1, 17)
        ])

        response = self.client.get(
            reverse('catalog:product_type', args=[Product.Category.SINK])
        )

        self.assertEqual(len(response.context['page_obj']), 15)
        self.assertTrue(response.context['page_obj'].has_next())

    def test_catalog_filters_can_be_combined(self):
        response = self.client.get(
            reverse('catalog:product_type', args=[Product.Category.SINK]),
            {
                'manufacturer': 'Nordic',
                'material': 'Фарфор',
                'color': 'Белый',
                'installation_type': Product.InstallationType.VANITY,
            },
        )

        self.assertContains(response, self.sink.name)
        self.assertNotContains(response, self.bathtub.name)

    def test_category_page_displays_only_database_filters(self):
        response = self.client.get(
            reverse('catalog:product_type', args=[Product.Category.SINK])
        )

        self.assertContains(response, 'data-dynamic-filter-form')
        self.assertContains(response, 'Производитель')
        self.assertContains(response, 'Nordic')
        self.assertContains(response, 'Цвет')
        self.assertContains(response, 'Белый')
        self.assertContains(response, 'Материал')
        self.assertContains(response, 'Фарфор')
        self.assertContains(response, 'Монтаж')
        self.assertNotContains(response, 'Применить')
        self.assertNotContains(response, 'Форма')
        self.assertNotContains(response, 'Размер')

    def test_popular_sort_is_not_available(self):
        response = self.client.get(
            reverse('catalog:product_type', args=[Product.Category.SINK]),
            {'sort': 'popular'},
        )

        self.assertEqual(response.context['sort'], 'name')
        self.assertNotContains(response, 'Популярные')

    def test_unknown_category_returns_404(self):
        response = self.client.get(reverse('catalog:product_type', args=['unknown']))
        self.assertEqual(response.status_code, 404)

    def test_product_detail_displays_characteristics_and_code(self):
        response = self.client.get(
            reverse('catalog:product_detail', args=[self.sink.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.sink.name)
        self.assertContains(response, self.sink.code)
        self.assertContains(response, 'Категория')
        self.assertContains(response, 'Размер')

    def test_product_detail_displays_gallery_images(self):
        ProductImage.objects.create(
            product=self.sink,
            image='products/gallery/test-extra.jpg',
            alt_text='Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅРѕРµ С„РѕС‚Рѕ',
            position=1,
        )

        response = self.client.get(
            reverse('catalog:product_detail', args=[self.sink.pk])
        )

        self.assertContains(response, 'data-gallery-open')
        self.assertContains(response, 'data-gallery-thumb')
        self.assertContains(response, 'data-gallery-prev')
        self.assertContains(response, 'data-gallery-next')
        self.assertContains(response, 'products/gallery/test-extra.jpg')
        self.assertContains(response, 'catalog/product-gallery.js')

    def test_catalog_card_links_to_product_detail(self):
        response = self.client.get(
            reverse('catalog:product_type', args=[Product.Category.SINK])
        )
        self.assertContains(
            response,
            reverse('catalog:product_detail', args=[self.sink.pk]),
        )

    def test_exact_product_name_search_redirects_to_detail(self):
        response = self.client.get(reverse('catalog:product_list'), {'q': self.sink.name})
        self.assertRedirects(
            response,
            reverse('catalog:product_detail', args=[self.sink.pk]),
            fetch_redirect_response=False,
        )

    def test_product_code_search_redirects_to_detail(self):
        response = self.client.get(reverse('catalog:product_list'), {'q': self.sink.code})
        self.assertRedirects(
            response,
            reverse('catalog:product_detail', args=[self.sink.pk]),
            fetch_redirect_response=False,
        )

    def test_unknown_product_code_shows_empty_search(self):
        response = self.client.get(reverse('catalog:product_list'), {'q': 'VD-999999'})
        self.assertEqual(response.context['page_obj'].paginator.count, 0)
        self.assertContains(response, 'Товар не найден')
        self.assertNotContains(response, 'Фильтры')
        self.assertNotContains(response, 'Сортировка')


class InformationPageTests(TestCase):
    def test_about_page_is_available(self):
        response = self.client.get(reverse('catalog:about'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'О магазине')
        self.assertContains(response, 'Как мы работаем')

    def test_contacts_page_contains_working_contact_links(self):
        response = self.client.get(reverse('catalog:contacts'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Контакты')
        self.assertContains(response, 'href="tel:+79550306398"')
        self.assertContains(response, reverse('home'))

    def test_footer_uses_real_navigation_links(self):
        response = self.client.get(reverse('catalog:about'))

        self.assertContains(response, reverse('catalog:product_list'))
        self.assertContains(response, reverse('users:profile'))
        self.assertContains(response, reverse('cart:detail'))
        self.assertContains(response, reverse('catalog:contacts'))
        self.assertNotContains(response, 'href="#"')


class SeedDemoDataCommandTests(TestCase):
    def test_command_creates_and_replaces_connected_demo_data(self):
        output = StringIO()
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            call_command(
                'seed_demo_data',
                products=7,
                users=2,
                orders=3,
                seed=123,
                stdout=output,
            )

            self.assertEqual(
                Product.objects.filter(description__startswith='[FAKER_DEMO]').count(),
                7,
            )
            self.assertGreaterEqual(
                ProductImage.objects.filter(
                    product__description__startswith='[FAKER_DEMO]'
                ).count(),
                14,
            )
            self.assertEqual(
                get_user_model().objects.filter(username__startswith='demo_').count(),
                2,
            )
            self.assertEqual(
                Order.objects.filter(user__username__startswith='demo_').count(),
                3,
            )
            self.assertEqual(
                UserProfile.objects.filter(user__username__startswith='demo_').count(),
                2,
            )
            self.assertTrue(all(
                product.image.storage.exists(product.image.name)
                for product in Product.objects.filter(
                    description__startswith='[FAKER_DEMO]'
                )
            ))
            self.assertTrue(all(
                image.image.storage.exists(image.image.name)
                for image in ProductImage.objects.filter(
                    product__description__startswith='[FAKER_DEMO]'
                )
            ))

            call_command(
                'seed_demo_data',
                products=1,
                users=1,
                orders=0,
                seed=321,
                clear=True,
                stdout=output,
            )

            self.assertEqual(
                Product.objects.filter(description__startswith='[FAKER_DEMO]').count(),
                1,
            )
            self.assertGreaterEqual(
                ProductImage.objects.filter(
                    product__description__startswith='[FAKER_DEMO]'
                ).count(),
                2,
            )
            self.assertEqual(
                get_user_model().objects.filter(username__startswith='demo_').count(),
                1,
            )


class ProductDimensionValidationTests(TestCase):
    def test_pipe_requires_length_and_diameter_only(self):
        pipe = Product(**product_data(
            category=Product.Category.PIPE,
            name='Труба 50 мм',
            width_cm=None,
            height_cm=None,
            diameter_cm=Decimal('5.00'),
        ))
        pipe.full_clean()

        pipe.diameter_cm = None
        with self.assertRaises(ValidationError) as error:
            pipe.full_clean()
        self.assertIn('diameter_cm', error.exception.message_dict)

    def test_other_category_has_no_dimensions(self):
        tool = Product(**product_data(
            category=Product.Category.OTHER,
            name='Сантехнический ключ',
            length_cm=None,
            width_cm=None,
            height_cm=None,
        ))
        tool.full_clean()
        self.assertEqual(tool.size_label, '')

    def test_standard_category_requires_three_dimensions(self):
        sink = Product(**product_data(width_cm=None))
        with self.assertRaises(ValidationError) as error:
            sink.full_clean()
        self.assertIn('width_cm', error.exception.message_dict)


class ProductAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(
            username='catalog_admin',
            email='admin@example.com',
            password='StrongPass123!',
        )

    def test_add_form_uses_fixed_category_and_image_preview_script(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:catalog_product_add'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="category"')
        self.assertContains(response, 'name="image"')
        self.assertContains(response, 'name="additional_images"')
        self.assertContains(response, 'multiple')
        self.assertContains(response, 'catalog/admin/product_form.js')
        self.assertNotContains(response, 'name="product_type"')
        self.assertNotContains(response, 'name="stock"')


class HomeRecommendationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.products = [
            Product.objects.create(**product_data(
                name=f'Товар {number}',
                price=Decimal('1000.00') + number,
            ))
            for number in range(1, 8)
        ]
        cls.user = get_user_model().objects.create_user(
            username='recommendation_user',
            password='StrongPass123',
        )

    def test_recommendations_are_saved_when_account_is_created(self):
        recommendations = ProductRecommendation.objects.filter(user=self.user)
        self.assertEqual(recommendations.count(), 5)
        self.assertEqual(
            list(recommendations.values_list('position', flat=True)),
            [1, 2, 3, 4, 5],
        )

    def test_authenticated_home_keeps_same_recommendations(self):
        self.client.force_login(self.user)
        initial_ids = list(
            self.user.product_recommendations.values_list('product_id', flat=True)
        )

        response = self.client.get(reverse('home'))
        self.client.get(reverse('home'))
        saved_ids = list(
            self.user.product_recommendations.values_list('product_id', flat=True)
        )

        self.assertEqual(initial_ids, saved_ids)
        self.assertContains(response, 'Рекомендуется')

    def test_guest_recommendations_are_stable_in_session(self):
        self.client.get(reverse('home'))
        first_ids = self.client.session['recommended_product_ids']
        self.client.get(reverse('home'))
        second_ids = self.client.session['recommended_product_ids']

        self.assertEqual(len(first_ids), 5)
        self.assertEqual(first_ids, second_ids)
