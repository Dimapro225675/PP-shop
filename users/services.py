from random import SystemRandom

from django.db import transaction

from catalog.models import Product

from .models import ProductRecommendation


RECOMMENDATION_LIMIT = 5


def initialize_user_recommendations(user):
    recommendations = user.product_recommendations.select_related('product')
    if recommendations.exists():
        return recommendations

    product_ids = list(Product.objects.values_list('pk', flat=True))
    if not product_ids:
        return recommendations

    selected_ids = SystemRandom().sample(
        product_ids,
        min(RECOMMENDATION_LIMIT, len(product_ids)),
    )
    with transaction.atomic():
        if not user.product_recommendations.exists():
            ProductRecommendation.objects.bulk_create(
                ProductRecommendation(
                    user=user,
                    product_id=product_id,
                    position=position,
                )
                for position, product_id in enumerate(selected_ids, start=1)
            )

    return user.product_recommendations.select_related('product')
