from uuid import uuid4

from django.db import migrations, models


def fill_idempotence_keys(apps, schema_editor):
    Order = apps.get_model('cart', 'Order')
    for order in Order.objects.filter(payment_idempotence_key__isnull=True).iterator():
        order.payment_idempotence_key = uuid4()
        order.save(update_fields=('payment_idempotence_key',))


class Migration(migrations.Migration):
    dependencies = [
        ('cart', '0004_order_hidden_from_history_alter_order_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('new', 'Новый'),
                    ('awaiting_payment', 'Ожидает оплаты'),
                    ('paid', 'Оплачен'),
                    ('payment_failed', 'Ошибка оплаты'),
                    ('delivered', 'Доставлен'),
                    ('cancelled', 'Отменён'),
                ],
                default='new',
                max_length=20,
                verbose_name='Статус',
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_confirmation_url',
            field=models.URLField(blank=True, verbose_name='Ссылка на оплату'),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_id',
            field=models.CharField(blank=True, db_index=True, max_length=64, verbose_name='ID платежа ЮKassa'),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_status',
            field=models.CharField(blank=True, max_length=32, verbose_name='Статус платежа ЮKassa'),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_idempotence_key',
            field=models.UUIDField(blank=True, null=True, verbose_name='Ключ идемпотентности'),
        ),
        migrations.RunPython(fill_idempotence_keys, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='order',
            name='payment_idempotence_key',
            field=models.UUIDField(default=uuid4, editable=False, unique=True, verbose_name='Ключ идемпотентности'),
        ),
    ]
