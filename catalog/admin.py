from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import Product, ProductImage


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        return [super(MultipleImageField, self).clean(item, initial) for item in data]


class ProductAdminForm(forms.ModelForm):
    additional_images = MultipleImageField(
        label='Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹Рµ С„РѕС‚РѕРіСЂР°С„РёРё',
        required=False,
        help_text='РњРѕР¶РЅРѕ РІС‹Р±СЂР°С‚СЊ СЃСЂР°Р·Сѓ РЅРµСЃРєРѕР»СЊРєРѕ С„Р°Р№Р»РѕРІ.',
    )

    class Meta:
        model = Product
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')

        if category == Product.Category.PIPE:
            cleaned_data['width_cm'] = None
            cleaned_data['height_cm'] = None
        elif category == Product.Category.OTHER:
            for field_name in ('length_cm', 'width_cm', 'height_cm', 'diameter_cm'):
                cleaned_data[field_name] = None
        else:
            cleaned_data['diameter_cm'] = None

        return cleaned_data


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ('image', 'image_preview', 'alt_text', 'position')
    readonly_fields = ('image_preview',)

    @admin.display(description='РџСЂРѕСЃРјРѕС‚СЂ')
    def image_preview(self, image):
        if not image or not image.image:
            return 'вЂ”'
        return format_html(
            '<img src="{}" alt="" style="width:84px;height:84px;object-fit:cover;'
            'border:1px solid #d8d8d8;border-radius:4px">',
            image.image.url,
        )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    inlines = (ProductImageInline,)
    list_display = (
        'image_thumbnail',
        'name',
        'category',
        'manufacturer',
        'price',
        'code_display',
    )
    list_filter = (
        'category',
        'installation_type',
        'manufacturer',
        'color',
        'material',
        'shape',
    )
    search_fields = ('name', 'manufacturer', 'description')
    readonly_fields = ('code_display', 'image_preview')
    fieldsets = (
        ('Основная информация', {
            'fields': (
                'category',
                'name',
                'price',
                'code_display',
                'description',
            ),
        }),
        ('Фотография', {
            'fields': ('image', 'image_preview', 'additional_images'),
        }),
        ('Характеристики', {
            'fields': (
                'material',
                'installation_type',
                'manufacturer',
                'color',
                'shape',
            ),
        }),
        ('Размер', {
            'fields': ('length_cm', 'width_cm', 'height_cm', 'diameter_cm'),
        }),
    )

    class Media:
        js = ('catalog/admin/product_form.js',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        images = request.FILES.getlist('additional_images')
        if not images:
            return
        start_position = obj.gallery_images.count()
        for index, image in enumerate(images, start=1):
            ProductImage.objects.create(
                product=obj,
                image=image,
                position=start_position + index,
            )

    @admin.display(description='Код товара')
    def code_display(self, product):
        return product.code if product and product.pk else 'Создаётся автоматически'

    @admin.display(description='Фото')
    def image_thumbnail(self, product):
        if not product.image:
            return '—'
        return format_html(
            '<img src="{}" alt="" style="width:56px;height:56px;object-fit:cover;border-radius:4px">',
            product.image.url,
        )

    @admin.display(description='Предварительный просмотр')
    def image_preview(self, product):
        image_url = product.image.url if product and product.image else ''
        display = 'block' if image_url else 'none'
        return format_html(
            '<img id="product-image-preview" src="{}" alt="Предварительный просмотр" '
            'style="display:{};max-width:480px;max-height:420px;object-fit:contain;'
            'border:1px solid #d8d8d8;border-radius:4px;padding:6px;background:#fff">',
            image_url,
            display,
        )
