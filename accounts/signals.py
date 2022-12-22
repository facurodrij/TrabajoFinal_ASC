from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=get_user_model())
def add_permissions_user(sender, instance, created, **kwargs):
    """
    Función para asignar todos los permisos a un usuario si es superusuario.
    """
    with transaction.atomic():
        if created:
            if instance.is_superuser or instance.is_staff:
                for permission in Permission.objects.all():
                    instance.user_permissions.add(permission)
            instance.save()
