from django import forms

from core.models import *


class UpdateClubForm(forms.ModelForm):
    """Formulario para actualizar el club."""
    nombre = forms.CharField(max_length=100,
                             required=True,
                             widget=forms.TextInput(attrs={'class': 'form-control'}))
    localidad = forms.Select(attrs={'class': 'form-control'})
    direccion = forms.CharField(max_length=100,
                                required=True,
                                widget=forms.TextInput(attrs={'class': 'form-control'}))
    logo = forms.ImageField(required=False,
                            widget=forms.FileInput(attrs={'class': 'form-control-file'}))

    class Meta:
        model = Club
        fields = ['nombre', 'localidad', 'direccion', 'imagen']
