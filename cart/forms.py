from django import forms

from .models import Order


class CheckoutForm(forms.Form):
    fulfillment_method = forms.ChoiceField(
        label='Способ получения',
        choices=Order.FulfillmentMethod.choices,
        initial=Order.FulfillmentMethod.DELIVERY,
        widget=forms.RadioSelect,
    )
    city = forms.CharField(
        label='Город',
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Город*'}),
    )
    street = forms.CharField(
        label='Улица',
        max_length=180,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Улица*'}),
    )
    house = forms.CharField(
        label='Дом',
        max_length=40,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Дом*'}),
    )
    entrance = forms.CharField(
        label='Подъезд',
        max_length=40,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Подъезд'}),
    )
    apartment = forms.CharField(
        label='Кв./офис',
        max_length=40,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Кв./офис'}),
    )
    comment = forms.CharField(
        label='Комментарий к заказу',
        required=False,
        widget=forms.Textarea(attrs={'placeholder': 'Комментарий к заказу', 'rows': 3}),
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('fulfillment_method') != Order.FulfillmentMethod.DELIVERY:
            return cleaned_data

        required_fields = ('city', 'street', 'house')
        for field_name in required_fields:
            if not cleaned_data.get(field_name):
                self.add_error(field_name, 'Обязательное поле')
        return cleaned_data
