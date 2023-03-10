from django import forms
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import Persona
from socios.models import Parameters


@receiver(post_save, sender=Persona)
def post_save_persona(sender, instance, created, **kwargs):
    """
    Este método debe ejecutarse después de guardar el formulario.
    """
    edad_minima_titular = Parameters.objects.get(club=instance.club).edad_minima_titular
    if instance.es_titular():
        if instance.get_edad() < edad_minima_titular:
            raise forms.ValidationError(
                'La persona al ser menor de {} años, debe tener una persona a cargo.'.format(edad_minima_titular))
    else:
        # No se puede seleccionar una persona_titular que no sea titular.
        if not instance.persona_titular.es_titular():
            raise forms.ValidationError('La persona a cargo seleccionada no es titular.')
        # Si la persona no es titular, no puede tener personas a su cargo.
        if instance.persona_set.exists():
            raise forms.ValidationError('No se puede seleccionar una persona a cargo, porque {} ya tiene '
                                        'personas a su cargo.'.format(instance.get_full_name()))
