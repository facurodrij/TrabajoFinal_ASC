from django import forms
from accounts.models import User

from .models import *


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
        fields = ['nombre', 'localidad', 'direccion', 'logo']


class SocioForm(forms.ModelForm):
    """Formulario para crear un socio."""

    def __init__(self, *args, **kwargs):
        super(SocioForm, self).__init__(*args, **kwargs)
        # Excluir los usuario que ya son socios y los que forman parte del grupo Administrador del club
        self.fields['user'].queryset = User.objects.exclude(socio__isnull=False).exclude(
            groups__name='Administrador del club').exclude(is_superuser=True)
        # Si se esta actualizando un socio incluir su usuario en el queryset
        if self.instance.pk:
            self.fields['user'].queryset = User.objects.filter(pk=self.instance.user.pk)

    class Meta:
        model = Socio
        fields = ['user', 'categoria', 'estado', 'is_inscripto']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'is_inscripto': forms.CheckboxInput(attrs={'id': 'check_inscripto'}),
        }
