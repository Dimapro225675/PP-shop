from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from yookassa import Configuration, Payment


class PaymentGatewayError(RuntimeError):
    pass


@dataclass(frozen=True)
class PaymentData:
    payment_id: str
    status: str
    amount: Decimal
    currency: str
    metadata: dict
    confirmation_url: str = ''


def _configure():
    if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
        raise PaymentGatewayError('Не настроены тестовые ключи ЮKassa')
    Configuration.configure(
        settings.YOOKASSA_SHOP_ID,
        settings.YOOKASSA_SECRET_KEY,
    )


def _payment_data(response):
    confirmation = getattr(response, 'confirmation', None)
    return PaymentData(
        payment_id=response.id,
        status=response.status,
        amount=Decimal(response.amount.value),
        currency=response.amount.currency,
        metadata=dict(response.metadata or {}),
        confirmation_url=(
            getattr(confirmation, 'confirmation_url', '')
            if confirmation
            else ''
        ),
    )


def create_payment(order, return_url):
    _configure()
    payload = {
        'amount': {
            'value': f'{order.total_amount:.2f}',
            'currency': 'RUB',
        },
        'capture': True,
        'confirmation': {
            'type': 'redirect',
            'return_url': return_url,
        },
        'description': f'Заказ №{order.pk} в магазине Vodopad',
        'metadata': {
            'order_id': str(order.pk),
            'user_id': str(order.user_id),
        },
    }
    try:
        response = Payment.create(payload, str(order.payment_idempotence_key))
    except Exception as error:
        raise PaymentGatewayError('ЮKassa временно недоступна') from error
    return _payment_data(response)


def get_payment(payment_id):
    _configure()
    try:
        response = Payment.find_one(payment_id)
    except Exception as error:
        raise PaymentGatewayError('Не удалось проверить статус платежа') from error
    return _payment_data(response)
