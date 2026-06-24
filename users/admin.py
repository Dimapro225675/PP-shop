from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .admin_forms import AdminUserChangeForm, AdminUserCreationForm
from .models import Favorite, ProductRecommendation


User = get_user_model()
admin.site.unregister(User)


@admin.register(User)
class VodopadUserAdmin(UserAdmin):
    add_form = AdminUserCreationForm
    form = AdminUserChangeForm
    list_display = (
        'username',
        'email',
        'full_name_display',
        'phone_display',
        'role_display',
        'is_active',
    )
    list_filter = ('is_staff', 'is_active')
    search_fields = (
        'username',
        'email',
        'profile__full_name',
        'profile__phone',
    )
    ordering = ('username',)
    filter_horizontal = ()
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Данные пользователя', {
            'fields': ('full_name', 'phone', 'email', 'role'),
        }),
        ('Статус', {'fields': ('is_active', 'last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'full_name',
                'phone',
                'email',
                'role',
                'password1',
                'password2',
            ),
        }),
    )
    readonly_fields = ('last_login', 'date_joined')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        form.save_profile(obj)

    @admin.display(description='ФИО', ordering='profile__full_name')
    def full_name_display(self, user):
        return getattr(getattr(user, 'profile', None), 'full_name', '—')

    @admin.display(description='Номер телефона', ordering='profile__phone')
    def phone_display(self, user):
        return getattr(getattr(user, 'profile', None), 'phone', '—')

    @admin.display(description='Роль', ordering='is_staff')
    def role_display(self, user):
        return 'Администратор' if user.is_staff else 'Пользователь'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    search_fields = ('user__username', 'product__name')
    list_select_related = ('user', 'product')


@admin.register(ProductRecommendation)
class ProductRecommendationAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'position', 'created_at')
    list_filter = ('position',)
    search_fields = ('user__username', 'product__name')
    list_select_related = ('user', 'product')
