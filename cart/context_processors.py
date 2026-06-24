from .cart import CART_SESSION_KEY


def cart_summary(request):
    quantities = request.session.get(CART_SESSION_KEY, {})
    return {'cart_item_count': sum(quantities.values())}
