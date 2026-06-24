from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils import timezone

from catalog.models import Product


def default_delivery_date():
    return timezone.localdate() + timedelta(days=7)


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Новый'
        AWAITING_PAYMENT = 'awaiting_payment', 'Ожидает оплаты'
        PAID = 'paid', 'Оплачен'
        PAYMENT_FAILED = 'payment_failed', 'Ошибка оплаты'
        SHIPPED = 'shipped', 'Доставляется'
        DELIVERED = 'delivered', 'Доставлен'
        CANCELLED = 'cancelled', 'Отменён'

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
