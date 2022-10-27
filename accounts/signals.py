from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission


@receiver(post_save, sender=get_user_model())
def add_permissions_user(sender, instance, created, **kwargs):
    """
    Función para asignar permisos a un usuario cuando se crea.
    """
    if created:
        try:
            if instance.is_superuser or instance.is_staff:
                # Asignar todos los permisos al superusuario
                for perm in Permission.objects.all():
                    instance.user_permissions.add(perm)
        except Exception as e:
            print(e)
