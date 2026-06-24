import re

from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import UserProfile


class AdminUserProfileFormMixin:
    ROLE_USER = 'user'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = (
        (ROLE_USER, 'Пользователь'),
        (ROLE_ADMIN, 'Администратор'),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['role'].initial = self.ROLE_USER
            return

        self.fields['role'].initial = (
            self.ROLE_ADMIN if self.instance.is_staff else self.ROLE_USER
        )
        try:
            profile = self.instance.profile
        except UserProfile.DoesNotExist:
            return
        self.fields['full_name'].initial = profile.full_name
        self.fields['phone'].initial = profile.phone

    def clean_full_name(self):
        full_name = self.cleaned_data['full_name'].strip()
        if not re.fullmatch(r'[А-Яа-яЁё\s-]+', full_name):
            raise ValidationError('ФИО должно содержать кириллицу, пробелы или дефисы')
        return full_name

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        if not re.fullmatch(r'8\(\d{3}\)\d{3}-\d{2}-\d{2}', phone):
            raise ValidationError('Телефон должен быть в формате 8(XXX)XXX-XX-XX')
        profiles = UserProfile.objects.filter(phone=phone)
        if self.instance.pk:
            profiles = profiles.exclude(user=self.instance)
        if profiles.exists():
            raise ValidationError('Пользователь с таким телефоном уже существует')
        return phone

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        users = self._meta.model.objects.filter(email__iexact=email)
        if self.instance.pk:
            users = users.exclude(pk=self.instance.pk)
        if users.exists():
            raise ValidationError('Пользователь с таким Email уже существует')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        is_admin = self.cleaned_data['role'] == self.ROLE_ADMIN
        user.email = self.cleaned_data['email']
        user.is_staff = is_admin
        user.is_superuser = is_admin
        if commit:
            user.save()
            self.save_profile(user)
        return user

    def save_profile(self, user):
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'full_name': self.cleaned_data['full_name'],
                'phone': self.cleaned_data['phone'],
            },
        )


class AdminUserCreationForm(AdminUserProfileFormMixin, UserCreationForm):
    full_name = forms.CharField(label='ФИО', max_length=150, required=True)
    phone = forms.CharField(label='Номер телефона', max_length=16, required=True)
    email = forms.EmailField(label='Email', required=True)
    role = forms.ChoiceField(
        label='Роль',
        choices=AdminUserProfileFormMixin.ROLE_CHOICES,
        required=True,
    )

    class Meta(UserCreationForm.Meta):
        fields = ('username', 'email')


class AdminUserChangeForm(AdminUserProfileFormMixin, UserChangeForm):
    full_name = forms.CharField(label='ФИО', max_length=150, required=True)
    phone = forms.CharField(label='Номер телефона', max_length=16, required=True)
    email = forms.EmailField(label='Email', required=True)
    role = forms.ChoiceField(
        label='Роль',
        choices=AdminUserProfileFormMixin.ROLE_CHOICES,
        required=True,
    )

    class Meta(UserChangeForm.Meta):
        fields = ('username', 'email', 'is_active')
