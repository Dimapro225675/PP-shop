import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import UserProfile


User = get_user_model()


class RegisterForm(UserCreationForm):
    full_name = forms.CharField(label='ФИО', max_length=150)
    phone = forms.CharField(label='Телефон', max_length=16)
    email = forms.EmailField(label='Email')

    class Meta:
        model = User
        fields = ('username', 'full_name', 'phone', 'email', 'password1', 'password2')
        labels = {'username': 'Логин'}

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not re.fullmatch(r'[A-Za-z0-9]+', username):
            raise ValidationError('Логин должен содержать только латинские буквы и цифры')
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Пользователь с таким логином уже существует')
        return username

    def clean_full_name(self):
        full_name = self.cleaned_data.get('full_name', '').strip()
        if not re.fullmatch(r'[А-Яа-яЁё\s-]+', full_name):
            raise ValidationError('ФИО должно содержать кириллицу, пробелы или дефисы')
        return full_name

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not re.fullmatch(r'8\(\d{3}\)\d{3}-\d{2}-\d{2}', phone):
            raise ValidationError('Телефон должен быть в формате 8(XXX)XXX-XX-XX')
        if UserProfile.objects.filter(phone=phone).exists():
            raise ValidationError('Пользователь с таким телефоном уже существует')
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Пользователь с таким Email уже существует')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
            UserProfile.objects.create(
                user=user,
                full_name=self.cleaned_data['full_name'],
                phone=self.cleaned_data['phone'],
            )
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Логин', max_length=150)
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)
