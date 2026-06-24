# Vodopad

Учебный интернет-магазин сантехники на Django без DRF. В проекте реализованы каталог и фильтрация, корзина, личный кабинет, избранное, заказы, роли пользователей и тестовая оплата через ЮKassa.

## Запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install poetry
python -m poetry install
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

Перед запуском заполните параметры PostgreSQL и тестовые ключи ЮKassa в `.env`.

## Тестовые данные

Создать демонстрационные товары, пользователей и заказы:

```powershell
python manage.py seed_demo_data --clear
```

Удалить только данные, созданные Faker:

```powershell
python manage.py seed_demo_data --clear --products 0 --users 0 --orders 0
```

## Тесты

```powershell
python manage.py test
```
