from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('catalog', '0003_product_stock'),
        ('users', '0002_favorite'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductRecommendation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveSmallIntegerField(verbose_name='Позиция')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создана')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recommended_to', to='catalog.product', verbose_name='Товар')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_recommendations', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Рекомендация товара',
                'verbose_name_plural': 'Рекомендации товаров',
                'ordering': ('position',),
            },
        ),
        migrations.AddConstraint(
            model_name='productrecommendation',
            constraint=models.UniqueConstraint(fields=('user', 'product'), name='unique_user_recommended_product'),
        ),
        migrations.AddConstraint(
            model_name='productrecommendation',
            constraint=models.UniqueConstraint(fields=('user', 'position'), name='unique_user_recommendation_position'),
        ),
        migrations.AddConstraint(
            model_name='productrecommendation',
            constraint=models.CheckConstraint(condition=models.Q(('position__gte', 1), ('position__lte', 5)), name='recommendation_position_between_1_and_5'),
        ),
    ]
