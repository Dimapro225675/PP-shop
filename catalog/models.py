from pathlib import Path
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models


def product_image_upload_path(instance, filename):
    extension = Path(filename).suffix.lower() or '.jpg'
    return f'products/{instance.category}/{uuid4().hex}{extension}'


def product_gallery_image_upload_path(instance, filename):
    extension = Path(filename).suffix.lower() or '.jpg'
    category = instance.product.category if instance.product_id else 'gallery'
    return f'products/{category}/gallery/{uuid4().hex}{extension}'


class Product(models.Model):
    class Category(models.TextChoices):
        BATHTUB = 'bathtub', 'Ванны'
        SINK = 'sink', 'Раковины'
        FAUCET = 'faucet', 'Краны'
        SHOWER = 'shower', 'Душевые'
        TOILET = 'toilet', 'Унитазы'
        PIPE = 'pipe', 'Трубы'
        OTHER = 'other', 'Другое'

    class InstallationType(models.TextChoices):
        WALL_MOUNTED = 'wall_mounted', 'Подвесной'
        VANITY = 'vanity', 'На тумбе'
        FLOOR_STANDING = 'floor_standing', 'Напольный'
        BUILT_IN = 'built_in', 'Встраиваемый'
        COUNTERTOP = 'countertop', 'Накладной'
        OTHER = 'other', 'Другой'

    category = models.CharField(
        'Категория',
        max_length=20,
        choices=Category.choices,
    )
    name = models.CharField('Название', max_length=200)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    image = models.ImageField(
        'Фотография',
        upload_to=product_image_upload_path,
    )
    description = models.TextField('Описание', blank=True)
    material = models.CharField('Материал', max_length=150)
    installation_type = models.CharField(
        'Монтаж',
        max_length=20,
        choices=InstallationType.choices,
    )
    manufacturer = models.CharField('Производитель', max_length=150)
    length_cm = models.DecimalField(
        'Длина, см',
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    width_cm = models.DecimalField(
        'Ширина, см',
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    height_cm = models.DecimalField(
        'Высота, см',
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    diameter_cm = models.DecimalField(
        'Диаметр трубы, см',
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    color = models.CharField('Цвет', max_length=100)
    shape = models.CharField('Форма', max_length=100)

    class Meta:
        ordering = ('name',)
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name='product_price_gte_0',
            ),
            models.CheckConstraint(
                condition=models.Q(length_cm__isnull=True) | models.Q(length_cm__gt=0),
                name='product_length_null_or_gt_0',
            ),
            models.CheckConstraint(
                condition=models.Q(width_cm__isnull=True) | models.Q(width_cm__gt=0),
                name='product_width_null_or_gt_0',
            ),
            models.CheckConstraint(
                condition=models.Q(height_cm__isnull=True) | models.Q(height_cm__gt=0),
                name='product_height_null_or_gt_0',
            ),
            models.CheckConstraint(
                condition=models.Q(diameter_cm__isnull=True) | models.Q(diameter_cm__gt=0),
                name='product_diameter_null_or_gt_0',
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}

        if self.category == self.Category.PIPE:
            if self.length_cm is None:
                errors['length_cm'] = 'Укажите длину одной трубы.'
            if self.diameter_cm is None:
                errors['diameter_cm'] = 'Укажите диаметр трубы.'
            if self.width_cm is not None:
                errors['width_cm'] = 'Для труб ширина не используется.'
            if self.height_cm is not None:
                errors['height_cm'] = 'Для труб высота не используется.'
        elif self.category == self.Category.OTHER:
            for field_name in ('length_cm', 'width_cm', 'height_cm', 'diameter_cm'):
                if getattr(self, field_name) is not None:
                    errors[field_name] = 'Для категории «Другое» размер не предусмотрен.'
        else:
            for field_name, label in (
                ('length_cm', 'длину'),
                ('width_cm', 'ширину'),
                ('height_cm', 'высоту'),
            ):
                if getattr(self, field_name) is None:
                    errors[field_name] = f'Укажите {label} товара.'
            if self.diameter_cm is not None:
                errors['diameter_cm'] = 'Диаметр используется только для труб.'

        if errors:
            raise ValidationError(errors)

    @property
    def code(self):
        return f'VD-{self.pk:06d}' if self.pk else ''

    @property
    def size_label(self):
        if self.category == self.Category.PIPE:
            if self.length_cm is None or self.diameter_cm is None:
                return ''
            return f'{self.length_cm:g} см × Ø {self.diameter_cm:g} см'
        if self.category == self.Category.OTHER:
            return ''
        if None in (self.length_cm, self.width_cm, self.height_cm):
            return ''
        return f'{self.length_cm:g} × {self.width_cm:g} × {self.height_cm:g} см'

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='gallery_images',
        verbose_name='Товар',
    )
    image = models.ImageField(
        'Фотография',
        upload_to=product_gallery_image_upload_path,
    )
    alt_text = models.CharField(
        'Описание фото',
        max_length=200,
        blank=True,
    )
    position = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        ordering = ('position', 'pk')
        verbose_name = 'Фотография товара'
        verbose_name_plural = 'Фотографии товара'

    def __str__(self):
        return self.alt_text or f'{self.product} #{self.pk}'
