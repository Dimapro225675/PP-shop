from decimal import Decimal

from catalog.models import Product


CART_SESSION_KEY = 'cart'
CART_SELECTED_SESSION_KEY = 'cart_selected'


class Cart:
    def __init__(self, request):
        self.user = getattr(request, 'user', None)
        self.session = request.session
        self.quantities = self._normalize_quantities(
            self.session.get(CART_SESSION_KEY, {})
        )
        if CART_SELECTED_SESSION_KEY in self.session:
            selected_ids = self.session.get(CART_SELECTED_SESSION_KEY, [])
        else:
            selected_ids = list(self.quantities)
        self.selected_ids = {
            str(product_id)
            for product_id in selected_ids
            if str(product_id) in self.quantities
        }

    @staticmethod
    def _normalize_quantities(quantities):
        normalized = {}
        for product_id, quantity in quantities.items():
            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                continue
            if quantity > 0:
                normalized[str(product_id)] = quantity
        return normalized

    def _user_can_persist(self):
        return bool(self.user and self.user.is_authenticated)

    def _persist_for_user(self):
        if not self._user_can_persist():
            return

        from .models import SavedCart

        if not self.quantities:
            SavedCart.objects.filter(user=self.user).delete()
            return

        SavedCart.objects.update_or_create(
            user=self.user,
            defaults={
                'quantities': self.quantities,
                'selected_ids': sorted(self.selected_ids),
            },
        )

    def _save(self):
        self.session[CART_SESSION_KEY] = self.quantities
        self.session[CART_SELECTED_SESSION_KEY] = sorted(self.selected_ids)
        self.session.modified = True
        self._persist_for_user()

    def persist_for_user(self):
        self._persist_for_user()

    def restore_for_user(self, user=None):
        if user is not None:
            self.user = user
        if not self._user_can_persist():
            return

        from .models import SavedCart

        saved_cart = SavedCart.objects.filter(user=self.user).first()
        if not saved_cart:
            self._save()
            return

        merged_quantities = self._normalize_quantities(saved_cart.quantities)
        for product_id, quantity in self.quantities.items():
            merged_quantities[product_id] = (
                merged_quantities.get(product_id, 0) + quantity
            )

        selected_ids = {
            str(product_id)
            for product_id in saved_cart.selected_ids
            if str(product_id) in merged_quantities
        }
        selected_ids.update(
            product_id
            for product_id in self.selected_ids
            if product_id in merged_quantities
        )

        self.quantities = merged_quantities
        self.selected_ids = selected_ids
        self._save()

    def add(self, product, quantity=1):
        if quantity < 1:
            raise ValueError('Количество должно быть больше нуля')

        product_id = str(product.pk)
        self.quantities[product_id] = self.quantities.get(product_id, 0) + quantity
        self.selected_ids.add(product_id)
        self._save()

    def update(self, product, quantity):
        if quantity <= 0:
            raise ValueError('Количество должно быть больше нуля')
        self.quantities[str(product.pk)] = quantity
        self._save()

    def set_selected(self, product_id, selected):
        product_id = str(product_id)
        if product_id not in self.quantities:
            raise KeyError(product_id)
        if selected:
            self.selected_ids.add(product_id)
        else:
            self.selected_ids.discard(product_id)
        self._save()

    def remove(self, product_id):
        product_id = str(product_id)
        self.quantities.pop(product_id, None)
        self.selected_ids.discard(product_id)
        self._save()

    def clear_products(self, product_ids):
        for product_id in product_ids:
            self.quantities.pop(str(product_id), None)
            self.selected_ids.discard(str(product_id))
        if self.quantities:
            self._save()
        else:
            self.clear()

    def clear(self):
        self.session.pop(CART_SESSION_KEY, None)
        self.session.pop(CART_SELECTED_SESSION_KEY, None)
        self.quantities = {}
        self.selected_ids = set()
        self.session.modified = True
        self._persist_for_user()

    def items(self):
        product_ids = [int(product_id) for product_id in self.quantities]
        products = Product.objects.filter(pk__in=product_ids).order_by('name')
        found_ids = {str(product.pk) for product in products}
        missing_ids = set(self.quantities) - found_ids
        if missing_ids:
            for product_id in missing_ids:
                self.quantities.pop(product_id, None)
                self.selected_ids.discard(product_id)
            self._save()

        return [
            {
                'product': product,
                'quantity': self.quantities[str(product.pk)],
                'total_price': product.price * self.quantities[str(product.pk)],
                'selected': str(product.pk) in self.selected_ids,
            }
            for product in products
        ]

    def selected_quantities(self):
        return {
            product_id: quantity
            for product_id, quantity in self.quantities.items()
            if product_id in self.selected_ids
        }

    def selected_total(self):
        return sum(
            (
                item['total_price']
                for item in self.items()
                if item['selected']
            ),
            start=Decimal('0.00'),
        )

    def __len__(self):
        return sum(self.quantities.values())
