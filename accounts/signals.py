from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from .models import Profile


@receiver(post_save, sender=get_user_model())
def create_profile(sender, instance, created, **kwargs):
    """Funcion para crear un perfil de usuario cuando se crea un usuario y asignarle los permisos de perfil."""
    Profile.objects.get_or_create(user=instance)
    try:
        instance.user_permissions.add(Permission.objects.get(codename='change_profile'))
    except Exception as e:
        print(e)


@receiver(post_save, sender=get_user_model())
def save_profile(sender, instance, **kwargs):
    """Funcion para guardar el perfil de usuario cuando se guarda un usuario."""
    instance.profile.save()
