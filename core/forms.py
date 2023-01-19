import mercadopago
from django import forms
from django.db import transaction
from django.forms import Form

from core.models import Club, Reserva, HoraLaboral
from parameters.models import Deporte
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
                    "expires": reserva.expira,
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
                # Si la preferencia devuelve un bad request, se elimina la reserva
                if preference_response["status"] == 400:
                    raise ConnectionError(
                        "Error al crear la preferencia de pago: " + preference_response["response"]["message"])
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


class ReservaIndexForm(Form):
    """Formulario para crear una reserva. Se usa en el index para que el usuario pueda elegir la cancha."""
    deporte = forms.ChoiceField(
        label='Deporte',
        choices=Deporte.objects.all().values_list('id', 'nombre'),
        widget=forms.Select()
    )
    fecha = forms.DateField(
        label='Fecha',
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}))
    hora = forms.ChoiceField(
        label='Hora',
        choices=HoraLaboral.objects.all().values_list('hora', 'hora'),
        widget=forms.Select()
    )


class ReservaUserForm(forms.ModelForm):
    """Formulario para crear una reserva. Se usa en el index para que el usuario pueda elegir la cancha."""
    hora = forms.ChoiceField(
        label='Hora',
        choices=HoraLaboral.objects.all().values_list('hora', 'hora'),
        widget=forms.Select()
    )

    def save(self, commit=True):
        reserva = super().save(commit=False)
        with transaction.atomic():
            hora = self.cleaned_data['hora']
            hora_laboral = HoraLaboral.objects.get(hora=self.cleaned_data['hora'])
            reserva.con_luz = reserva.cancha.canchahoralaboral_set.get(hora_laboral=hora_laboral).con_luz
            reserva.expira = True
            reserva.forma_pago = 2
            reserva.save()
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
        fields = ['cancha', 'fecha', 'hora', 'nota', 'nombre', 'email']
        widgets = {
            'cancha': forms.Select(attrs={'disabled': True}),
            'fecha': forms.DateInput(attrs={'class': 'form-control'}),
            'nota': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su nombre'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su email'}),
            # TODO: Si el usuario esta autenticado, que se complete el email y el nombre
        }
