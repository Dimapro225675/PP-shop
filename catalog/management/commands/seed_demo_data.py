from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from random import Random

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from faker import Faker

from cart.models import Order, OrderItem
from catalog.models import Product, ProductImage
from users.models import Favorite, UserProfile


DEMO_MARKER = '[FAKER_DEMO]'
DEMO_PASSWORD = 'DemoPass123!'

CATEGORY_DATA = {
    Product.Category.BATHTUB: ('Ванна', 'bathtub.png'),
    Product.Category.SINK: ('Раковина', 'sinks.png'),
    Product.Category.FAUCET: ('Смеситель', 'faucet.png'),
    Product.Category.SHOWER: ('Душевая система', 'showers.png'),
    Product.Category.TOILET: ('Унитаз', 'toilet.png'),
    Product.Category.PIPE: ('Труба', 'pipe.png'),
    Product.Category.OTHER: ('Сантехнический инструмент', 'other.png'),
}


class Command(BaseCommand):
    help = 'Создаёт связанные демонстрационные данные с помощью Faker.'

    def add_arguments(self, parser):
        parser.add_argument('--products', type=int, default=28)
        parser.add_argument('--users', type=int, default=8)
        parser.add_argument('--orders', type=int, default=12)
        parser.add_argument('--seed', type=int, default=2026)
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Удалить только ранее созданные этой командой демо-данные.',
        )

    def handle(self, *args, **options):
        for option in ('products', 'users', 'orders'):
            if options[option] < 0:
                raise CommandError(f'Параметр --{option} не может быть отрицательным.')
        if options['orders'] and (not options['products'] or not options['users']):
            raise CommandError('Для заказов требуется хотя бы один товар и пользователь.')

        fake = Faker('ru_RU')
        fake.seed_instance(options['seed'])
        random = Random(options['seed'])

        with transaction.atomic():
            if options['clear']:
                self._clear_demo_data()
            products = self._create_products(fake, random, options['products'])
            users = self._create_users(fake, options['users'])
            orders = self._create_orders(random, users, products, options['orders'])
            self._create_favorites(random, users, products)

        self.stdout.write(self.style.SUCCESS(
            f'Создано: товаров — {len(products)}, пользователей — {len(users)}, '
            f'заказов — {len(orders)}.'
        ))
        if users:
            self.stdout.write(
                f'Демо-пароль для пользователей: {DEMO_PASSWORD}'
            )

    def _clear_demo_data(self):
        demo_orders = Order.objects.filter(
            Q(user__username__startswith='demo_')
            | Q(items__product__description__startswith=DEMO_MARKER)
        ).distinct()
        demo_orders.delete()
        get_user_model().objects.filter(username__startswith='demo_').delete()

        products = list(Product.objects.filter(description__startswith=DEMO_MARKER))
        for product in products:
            for gallery_image in product.gallery_images.all():
                if gallery_image.image:
                    gallery_image.image.delete(save=False)
            if product.image:
                product.image.delete(save=False)
        Product.objects.filter(pk__in=[product.pk for product in products]).delete()

    def _create_products(self, fake, random, count):
        categories = list(CATEGORY_DATA)
        installations = list(Product.InstallationType.values)
        materials = ('акрил', 'фарфор', 'латунь', 'сталь', 'полипропилен')
        colors = ('белый', 'чёрный', 'хром', 'серый', 'бежевый')
        shapes = ('прямоугольная', 'овальная', 'круглая', 'квадратная')
        brands = ('Aquatek', 'Santek', 'Roca', 'Grohe', 'Vodopad Home')
        image_directory = (
            Path(settings.BASE_DIR) / 'catalog' / 'static' / 'catalog'
            / 'images' / 'categories'
        )
        products = []

        for index in range(count):
            category = categories[index % len(categories)]
            product_label, image_name = CATEGORY_DATA[category]
            product = Product(
                category=category,
                name=f'{product_label} {fake.word().capitalize()} {index + 1}',
                price=Decimal(random.randrange(1500, 90001)),
                description=(
                    f'{DEMO_MARKER} {fake.text(max_nb_chars=180)}'
                ),
                material=random.choice(materials),
                installation_type=random.choice(installations),
                manufacturer=random.choice(brands),
                color=random.choice(colors),
                shape=random.choice(shapes),
            )
            if category == Product.Category.PIPE:
                product.length_cm = Decimal(random.choice((100, 200, 300, 600)))
                product.diameter_cm = Decimal(random.choice((2, 3, 5, 10, 15)))
            elif category != Product.Category.OTHER:
                product.length_cm = Decimal(random.randrange(40, 201))
                product.width_cm = Decimal(random.randrange(30, 101))
                product.height_cm = Decimal(random.randrange(10, 91))

            image_path = image_directory / image_name
            with image_path.open('rb') as image_file:
                product.image.save(image_name, File(image_file), save=False)
            product.full_clean()
            product.save()
            self._create_product_gallery(product, product_label, image_path, random)
            products.append(product)

        return products

    def _create_product_gallery(self, product, product_label, image_path, random):
        gallery_count = random.randint(2, 3)
        gallery_images = []
        for position in range(1, gallery_count + 1):
            gallery_image = ProductImage(
                product=product,
                alt_text=f'{product_label} {product.name} - фото {position + 1}',
                position=position,
            )
            with image_path.open('rb') as image_file:
                gallery_image.image.save(
                    f'{image_path.stem}-gallery-{position}{image_path.suffix}',
                    File(image_file),
                    save=False,
                )
            gallery_image.full_clean()
            gallery_images.append(gallery_image)

        ProductImage.objects.bulk_create(gallery_images)

    def _create_users(self, fake, count):
        User = get_user_model()
        users = []
        candidate_index = 1

        while len(users) < count:
            username = f'demo_{candidate_index:04d}'
            phone = self._phone(candidate_index)
            candidate_index += 1
            if User.objects.filter(username=username).exists():
                continue
            if UserProfile.objects.filter(phone=phone).exists():
                continue

            is_admin = not users
            user = User.objects.create_user(
                username=username,
                email=f'{username}@example.com',
                password=DEMO_PASSWORD,
                is_staff=is_admin,
                is_superuser=is_admin,
            )
            UserProfile.objects.create(
                user=user,
                full_name=fake.name(),
                phone=phone,
            )
            users.append(user)

        return users

    def _create_orders(self, random, users, products, count):
        statuses = (
            Order.Status.PAID,
            Order.Status.SHIPPED,
            Order.Status.DELIVERED,
            Order.Status.CANCELLED,
        )
        orders = []

        for index in range(count):
            selected_products = random.sample(
                products,
                k=random.randint(1, min(3, len(products))),
            )
            status = random.choice(statuses)
            order = Order.objects.create(
                user=random.choice(users),
                status=status,
                delivery_date=(
                    timezone.localdate() + timedelta(days=random.randint(-10, 14))
                ),
                payment_id=f'demo-payment-{index + 1}',
                payment_status='succeeded',
            )
            total = Decimal('0')
            for product in selected_products:
                quantity = random.randint(1, 4)
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    unit_price=product.price,
                    quantity=quantity,
                )
                total += product.price * quantity
            order.total_amount = total
            order.save(update_fields=('total_amount',))
            orders.append(order)

        return orders

    def _create_favorites(self, random, users, products):
        for user in users:
            selected_products = random.sample(
                products,
                k=min(random.randint(1, 4), len(products)),
            )
            Favorite.objects.bulk_create(
                Favorite(user=user, product=product)
                for product in selected_products
            )

    @staticmethod
    def _phone(index):
        area_code = 900 + ((index // 10_000_000) % 100)
        subscriber = f'{index % 10_000_000:07d}'
        return (
            f'8({area_code:03d}){subscriber[:3]}-'
            f'{subscriber[3:5]}-{subscriber[5:]}'
        )
