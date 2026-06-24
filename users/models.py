from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь',
    )
    full_name = models.CharField('ФИО', max_length=150)
    phone = models.CharField('Телефон', max_length=16, unique=True)

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    @property
    def role_name(self):
        return 'Администратор' if self.user.is_staff else 'Пользователь'

    def __str__(self):
        return self.full_name


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь',
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='Товар',
    )
    created_at = models.DateTimeField('Добавлен', auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Избранный товар'
        verbose_name_plural = 'Избранные товары'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'product'),
                name='unique_user_favorite_product',
            ),
        ]

    def __str__(self):
        return f'{self.user} — {self.product}'


class ProductRecommendation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='product_recommendations',
        verbose_name='Пользователь',
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='recommended_to',
        verbose_name='Товар',
    )
    position = models.PositiveSmallIntegerField('Позиция')
    created_at = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        ordering = ('position',)
        verbose_name = 'Рекомендация товара'
        verbose_name_plural = 'Рекомендации товаров'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'product'),
                name='unique_user_recommended_product',
            ),
            models.UniqueConstraint(
                fields=('user', 'position'),
                name='unique_user_recommendation_position',
            ),
            models.CheckConstraint(
                condition=models.Q(position__gte=1, position__lte=5),
                name='recommendation_position_between_1_and_5',
            ),
        ]

    def __str__(self):
        return f'{self.user}: {self.product}'
