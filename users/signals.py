from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .services import initialize_user_recommendations


@receiver(post_save, sender=get_user_model())
def create_product_recommendations(sender, instance, created, **kwargs):
    if created:
        initialize_user_recommendations(instance)
