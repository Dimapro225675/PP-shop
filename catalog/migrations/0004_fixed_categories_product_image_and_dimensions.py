import catalog.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0003_product_stock'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='product',
            name='product_length_gt_0',
        ),
        migrations.RemoveConstraint(
            model_name='product',
            name='product_width_gt_0',
        ),
        migrations.RemoveConstraint(
            model_name='product',
            name='product_height_gt_0',
        ),
        migrations.RemoveField(
            model_name='product',
            name='category',
        ),
        migrations.DeleteModel(
            name='Category',
        ),
        migrations.RenameField(
            model_name='product',
            old_name='product_type',
            new_name='category',
        ),
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.CharField(
                choices=[
                    ('bathtub', 'Ванны'),
                    ('sink', 'Раковины'),
                    ('faucet', 'Краны'),
                    ('shower', 'Душевые'),
                    ('toilet', 'Унитазы'),
                    ('pipe', 'Трубы'),
                    ('other', 'Другое'),
                ],
                max_length=20,
                verbose_name='Категория',
            ),
        ),
        migrations.RemoveField(
            model_name='product',
            name='stock',
        ),
        migrations.AlterField(
            model_name='product',
            name='length_cm',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='Длина, см'),
        ),
        migrations.AlterField(
            model_name='product',
            name='width_cm',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='Ширина, см'),
        ),
        migrations.AlterField(
            model_name='product',
            name='height_cm',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='Высота, см'),
        ),
        migrations.AddField(
            model_name='product',
            name='diameter_cm',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='Диаметр трубы, см'),
        ),
        migrations.AddField(
            model_name='product',
            name='image',
            field=models.ImageField(default='', upload_to=catalog.models.product_image_upload_path, verbose_name='Фотография'),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.CheckConstraint(condition=models.Q(('length_cm__isnull', True), ('length_cm__gt', 0), _connector='OR'), name='product_length_null_or_gt_0'),
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.CheckConstraint(condition=models.Q(('width_cm__isnull', True), ('width_cm__gt', 0), _connector='OR'), name='product_width_null_or_gt_0'),
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.CheckConstraint(condition=models.Q(('height_cm__isnull', True), ('height_cm__gt', 0), _connector='OR'), name='product_height_null_or_gt_0'),
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.CheckConstraint(condition=models.Q(('diameter_cm__isnull', True), ('diameter_cm__gt', 0), _connector='OR'), name='product_diameter_null_or_gt_0'),
        ),
    ]
