from django import forms
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.admin.widgets import AdminFileWidget

from .models import Tipo, Estado


class ElegirTipoForm(forms.Form):
    """
    Formulario para el paso 1 de una solicitud de asociación.
    """
    # Paso 1: Elegir el tipo de socio.
    tipo = forms.ModelChoiceField(required=True,
                                  queryset=Tipo.objects.all(),
                                  widget=forms.Select(attrs={'class': 'form-control select2'}))


class ElegirEstadoForm(forms.Form):
    """
    Formulario para elegir un estado de socio.
    """
    estado = forms.ModelChoiceField(required=True,
                                    queryset=Estado.objects.all(),
                                    widget=forms.Select(attrs={'class': 'form-control select2'}))


