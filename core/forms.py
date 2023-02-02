import mercadopago
from django import forms

from core.models import Club
from static.credentials import MercadoPagoCredentials

public_key = MercadoPagoCredentials.get_public_key()
access_token = MercadoPagoCredentials.get_access_token()
sdk = mercadopago.SDK(access_token)


class ClubForm(forms.ModelForm):
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
