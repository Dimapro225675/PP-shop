from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils import timezone

from catalog.models import Product


def default_delivery_date():
    return timezone.localdate() + timedelta(days=7)


def default_delivery_cost():
    return 500


PICKUP_CITY = 'Белореченск'
PICKUP_STREET = 'Ленина 55'


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Новый'
        AWAITING_PAYMENT = 'awaiting_payment', 'Ожидает оплаты'
        PAID = 'paid', 'Оплачен'
        PAYMENT_FAILED = 'payment_failed', 'Ошибка оплаты'
        SHIPPED = 'shipped', 'Доставляется'
        DELIVERED = 'delivered', 'Доставлен'
        CANCELLED = 'cancelled', 'Отменён'

    class FulfillmentMethod(models.TextChoices):
        DELIVERY = 'delivery', 'Доставка'
        PICKUP = 'pickup', 'Самовывоз'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='orders',
        null=True,
        blank=True,
        verbose_name='Пользователь',
    )
    session_key = models.CharField('Ключ сессии', max_length=40, blank=True)
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    total_amount = models.DecimalField(
        'Сумма',
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    delivery_cost = models.DecimalField(
        'Стоимость доставки',
        max_digits=10,
        decimal_places=2,
        default=default_delivery_cost,
    )
    fulfillment_method = models.CharField(
        'Способ получения',
        max_length=20,
        choices=FulfillmentMethod.choices,
        default=FulfillmentMethod.DELIVERY,
    )
    delivery_city = models.CharField('Город доставки', max_length=120, blank=True)
    delivery_street = models.CharField('Улица', max_length=180, blank=True)
    delivery_house = models.CharField('Дом', max_length=40, blank=True)
    delivery_apartment = models.CharField('Кв./офис', max_length=40, blank=True)
    delivery_entrance = models.CharField('Подъезд', max_length=40, blank=True)
    delivery_comment = models.TextField('Комментарий к заказу', blank=True)
    delivery_date = models.DateField(
        'Дата доставки',
        default=default_delivery_date,
    )
    hidden_from_history = models.BooleanField(
        'Скрыт из истории',
        default=False,
    )
    payment_id = models.CharField(
        'ID платежа ЮKassa',
        max_length=64,
        blank=True,
        db_index=True,
    )
    payment_status = models.CharField(
        'Статус платежа ЮKassa',
        max_length=32,
        blank=True,
    )
    payment_confirmation_url = models.URLField(
        'Ссылка на оплату',
        blank=True,
    )
    payment_idempotence_key = models.UUIDField(
        'Ключ идемпотентности',
        default=uuid4,
        unique=True,
        editable=False,
    )
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    def __str__(self):
        return f'Заказ №{self.pk}'

    @property
    def is_pickup(self):
        return self.fulfillment_method == self.FulfillmentMethod.PICKUP

    @property
    def delivery_address_display(self):
        if self.is_pickup:
            return f'Самовывоз, Город: {PICKUP_CITY}; Улица: {PICKUP_STREET}'

        parts = []
        if self.delivery_city:
            parts.append(f'Город: {self.delivery_city}')
        if self.delivery_street:
            parts.append(f'Улица: {self.delivery_street}')
        if self.delivery_house:
            parts.append(f'Дом: {self.delivery_house}')
        if self.delivery_entrance:
            parts.append(f'Подъезд: {self.delivery_entrance}')
        if self.delivery_apartment:
            parts.append(f'Кв./офис: {self.delivery_apartment}')
        return '; '.join(parts)


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name='Товар',
    )
    product_name = models.CharField('Название товара', max_length=200)
    unit_price = models.DecimalField(
        'Цена за единицу',
        max_digits=10,
        decimal_places=2,
    )
    quantity = models.PositiveIntegerField('Количество')

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name='order_item_quantity_gt_0',
            ),
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=0),
                name='order_item_unit_price_gte_0',
            ),
        ]

    @property
    def total_price(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f'{self.product_name} × {self.quantity}'
