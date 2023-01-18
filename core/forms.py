import mercadopago

from django import forms
from django.db import transaction

from core.models import Club, Reserva, PagoReserva
from static.credentials import MercadoPagoCredentials

public_key = MercadoPagoCredentials.get_public_key()
access_token = MercadoPagoCredentials.get_access_token()
sdk = mercadopago.SDK(access_token)


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


class ReservaAdminForm(forms.ModelForm):
    """Formulario para crear una reserva."""
    # Campo forma de pago sean radio buttons
    forma_pago = forms.ChoiceField(
        label='Forma de pago',
        choices=Reserva.FORMA_PAGO,
        widget=forms.RadioSelect())
    # Campo hora un number input
    hora = forms.TimeField(
        label='Hora',
        widget=forms.TimeInput(
            attrs={'type': 'time', 'class': 'form-control'}))

    def save(self, commit=True):
        reserva = super().save(commit=False)
        with transaction.atomic():
            reserva.save()
            if reserva.forma_pago == 2:
                preference_data = {
                    "items": [
                        {
                            "title": reserva.__str__(),
                            "quantity": 1,
                            "currency_id": "ARS",
                            "unit_price": float(reserva.get_price()),
                            "description": "Reserva de cancha {}".format(reserva.cancha.club)
                        }
                    ],
                    "statement_descriptor": "Reserva de cancha {}".format(reserva.cancha.club),
                    "excluded_payment_types": [
                        {
                            "id": "ticket"
                        }
                    ],
                    "installments": 1,
                    "binary_mode": True,
                    "expires": True,
                    "expiration_date_from": reserva.created_at.isoformat(),
                    "expiration_date_to": reserva.get_expiration_date().isoformat(),
                    "back_urls": {
                        "success": "http://127.0.0.1:8000/reserva/checkout/",
                        "failure": "http://127.0.0.1:8000/reserva/checkout/",
                    },
                    "auto_return": "approved",
                    "external_reference": str(reserva.pk),
                }
                preference_response = sdk.preference().create(preference_data)
                preference = preference_response["response"]
                reserva.preference_id = preference["id"]
                reserva.save()
        return reserva

    class Meta:
        model = Reserva
        fields = ['cancha', 'nombre', 'email', 'fecha', 'hora', 'nota', 'forma_pago', 'con_luz', 'expira']
        widgets = {
            'cancha': forms.Select(attrs={'disabled': True}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el nombre'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el email'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control'}),
            'nota': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'con_luz': forms.CheckboxInput(),
            'expira': forms.CheckboxInput(),
        }
