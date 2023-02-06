import mercadopago
from django import forms
from django.forms import inlineformset_factory

from eventos.models import Evento, TicketVariante
from static.credentials import MercadoPagoCredentials

public_key = MercadoPagoCredentials.get_public_key()
access_token = MercadoPagoCredentials.get_access_token()
sdk = mercadopago.SDK(access_token)


class EventoForm(forms.ModelForm):
    """Formulario para crear un evento."""
    imagen = forms.ImageField(
        required=True,
        widget=forms.FileInput(attrs={'class': 'custom-file-input'}))

    class Meta:
        model = Evento
        fields = '__all__'
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el nombre del evento'}),
            'descripcion': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ingrese una descripción'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control'}),
            'hora_inicio': forms.TimeInput(attrs={'class': 'form-control'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control'}),
            'hora_fin': forms.TimeInput(attrs={'class': 'form-control'}),
            'registro_deadline': forms.DateInput(attrs={'class': 'form-control'}),
            'mayor_edad': forms.CheckboxInput(),
            'descuento_socio': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class TicketVarianteForm(forms.ModelForm):
    """Formulario para crear una variante de ticket."""

    class Meta:
        model = TicketVariante
        exclude = ['is_deleted', 'deleted_at']
        widgets = {
            'evento': forms.Select(attrs={'disabled': True}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el nombre del ticket'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el precio del ticket'}),
            'total_tickets': forms.NumberInput(
                attrs={'class': 'form-control', 'placeholder': 'Ingrese la cantidad de tickets'}),
        }


TicketVarianteFormSet = inlineformset_factory(
    Evento, TicketVariante, form=TicketVarianteForm, extra=0,
    can_delete=False, can_delete_extra=False, min_num=1, validate_min=True)
