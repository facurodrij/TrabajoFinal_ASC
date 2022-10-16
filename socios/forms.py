from django import forms
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.admin.widgets import AdminFileWidget

from .models import Tipo, SocioIndividual, User, Persona, Categoria, Estado
from accounts.models import UsuarioPersona
from core.models import Club
from parameters.models import Sexo, Localidad


# TODO: Crear un formulario para el modelo Categoria.
# TODO: Crear los formularios para crear un socio individual nuevo.
# TODO: Crear los formularios para crear un socio familiar nuevo.

class ElegirTipoForm(forms.Form):
    """
    Formulario para el paso 2 de una solicitud de asociación.
    """
    # Paso 1: Elegir el tipo de socio.
    tipo = forms.ModelChoiceField(required=True,
                                  queryset=Tipo.objects.filter(admite_miembro=False),
                                  widget=forms.Select(attrs={'class': 'form-control select2'}))
    # TODO: Permitir elegir el tipo de socio que admita miembros familiares.
