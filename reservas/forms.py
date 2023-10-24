import mercadopago
from django import forms
from django.db import transaction, ProgrammingError, OperationalError

from reservas.models import Reserva, HoraLaboral, Deporte, Parameters
from static.credentials import MercadoPagoCredentials

public_key = MercadoPagoCredentials.get_public_key()
access_token = MercadoPagoCredentials.get_access_token()
sdk = mercadopago.SDK(access_token)


class ReservaAdminForm(forms.ModelForm):
    """Formulario para crear una reserva."""
    HORAS = (
        ('00:00:00', '00:00 hs'),
        ('01:00:00', '01:00 hs'),
        ('02:00:00', '02:00 hs'),
        ('03:00:00', '03:00 hs'),
        ('04:00:00', '04:00 hs'),
        ('05:00:00', '05:00 hs'),
        ('06:00:00', '06:00 hs'),
        ('07:00:00', '07:00 hs'),
        ('08:00:00', '08:00 hs'),
        ('09:00:00', '09:00 hs'),
        ('10:00:00', '10:00 hs'),
        ('11:00:00', '11:00 hs'),
        ('12:00:00', '12:00 hs'),
        ('13:00:00', '13:00 hs'),
        ('14:00:00', '14:00 hs'),
        ('15:00:00', '15:00 hs'),
        ('16:00:00', '16:00 hs'),
        ('17:00:00', '17:00 hs'),
        ('18:00:00', '18:00 hs'),
        ('19:00:00', '19:00 hs'),
        ('20:00:00', '20:00 hs'),
        ('21:00:00', '21:00 hs'),
        ('22:00:00', '22:00 hs'),
        ('23:00:00', '23:00 hs'),
    )
    try:
        deporte = forms.ChoiceField(
            label='Deporte',
            choices=Deporte.objects.all().values_list('id', 'nombre'),
            widget=forms.Select()
        )
        # Campo forma de pago sean radio buttons
        forma_pago = forms.ChoiceField(
            label='Forma de pago',
            choices=Reserva.FORMA_PAGO,
            widget=forms.RadioSelect())
        # Campo hora un number input
        hora = forms.ChoiceField(
            label='Hora',
            choices=HORAS,
            widget=forms.Select())
        precio = forms.DecimalField(
            required=False,
            label='Precio',
            help_text='Si no se ingresa un precio, el sistema utilizará el precio definido en la cancha.',
            widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el precio (opcional)'}))
    except (ProgrammingError, OperationalError):
        pass

    def save(self, commit=True):
        reserva = super().save(commit=False)
        with transaction.atomic():
            reserva.expira = False if reserva.forma_pago == 1 else self.instance.expira
            if reserva.precio is None:
                reserva.precio = reserva.cancha.precio_luz if reserva.con_luz and reserva.cancha.precio_luz else reserva.cancha.precio
            reserva.save()
            if reserva.forma_pago == 2:
                preference_data = {
                    "items": [
                        {
                            "title": reserva.__str__(),
                            "quantity": 1,
                            "currency_id": "ARS",
                            "unit_price": float(reserva.precio),
                            "description": "Reserva de cancha {}".format(reserva.cancha.club)
                        }
                    ],
                    "payer": {
                        "name": reserva.nombre,
                        "email": reserva.email,
                    },
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
                    "expiration_date_to": reserva.get_expiration_date(),
                    "back_urls": {
                        "success": "http://127.0.0.1:8000/reservas/checkout/",
                        "failure": "http://127.0.0.1:8000/reservas/checkout/",
                    },
                    "auto_return": "approved",
                    "external_reference": str(reserva.pk),
                }
                try:
                    preference_response = sdk.preference().create(preference_data)
                except ConnectionError:
                    raise ConnectionError("Error al crear la preferencia de pago, revise las credenciales.")
                if preference_response["status"] == 400:
                    raise ConnectionError("Error al crear la preferencia de pago, revise las credenciales.")
                preference = preference_response["response"]
                reserva.preference_id = preference["id"]
                reserva.save()
        return reserva

    class Meta:
        model = Reserva
        fields = ['cancha', 'nombre', 'email', 'fecha', 'hora', 'nota', 'forma_pago', 'con_luz', 'expira', 'precio']
        widgets = {
            'cancha': forms.Select(attrs={'disabled': True}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el nombre'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el email'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control'}),
            'nota': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                          'placeholder': 'Ingrese una nota (opcional)'}),
            'con_luz': forms.CheckboxInput(),
            'expira': forms.CheckboxInput(),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el precio'}),
        }


class ReservaIndexForm(forms.Form):
    """Formulario para crear una reserva. Se usa en el index para que el usuario pueda elegir la cancha."""
    try:
        deporte = forms.ChoiceField(
            label='Deporte',
            required=True,
            choices=Deporte.objects.all().values_list('id', 'nombre'),
            widget=forms.Select()
        )
        fecha = forms.DateField(
            required=True,
            label='Fecha',
            widget=forms.DateInput(
                attrs={'class': 'form-control'}))
        hora = forms.ChoiceField(
            required=True,
            label='Hora',
            choices=HoraLaboral.objects.all().values_list('hora', 'hora'),
            widget=forms.Select()
        )
    except (ProgrammingError, OperationalError):
        pass


class ReservaUserForm(forms.ModelForm):
    """Formulario para crear una reserva. Se usa en el index para que el usuario pueda elegir la cancha."""
    try:
        deporte = forms.ChoiceField(
            label='Deporte',
            choices=Deporte.objects.all().values_list('id', 'nombre'),
            widget=forms.Select()
        )
        hora = forms.ChoiceField(
            label='Hora',
            choices=HoraLaboral.objects.all().values_list('hora', 'hora'),
            widget=forms.Select()
        )
    except (ProgrammingError, OperationalError):
        pass

    def save(self, commit=True):
        reserva = super().save(commit=False)
        with transaction.atomic():
            hora_laboral = HoraLaboral.objects.get(hora=self.cleaned_data['hora'])
            reserva.con_luz = reserva.cancha.canchahoralaboral_set.get(hora_laboral=hora_laboral).con_luz
            reserva.precio = reserva.cancha.precio_luz if reserva.con_luz and reserva.cancha.precio_luz else reserva.cancha.precio
            reserva.forma_pago = 2
            if commit:
                reserva.save()
                preference_data = {
                    "items": [
                        {
                            "title": reserva.__str__(),
                            "quantity": 1,
                            "currency_id": "ARS",
                            "unit_price": float(reserva.precio),
                            "description": "Reserva de cancha {}".format(reserva.cancha.club)
                        }
                    ],
                    "payer": {
                        "name": reserva.nombre,
                        "email": reserva.email,
                    },
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
                    "expiration_date_to": reserva.get_expiration_date(),
                    "back_urls": {
                        "success": "http://127.0.0.1:8000/reservas/checkout/",
                        "failure": "http://127.0.0.1:8000/reservas/checkout/",
                    },
                    "auto_return": "approved",
                    "external_reference": str(reserva.pk),
                }
                try:
                    preference_response = sdk.preference().create(preference_data)
                except ConnectionError:
                    raise ConnectionError("Error al crear la preferencia de pago, revise las credenciales.")
                if preference_response["status"] == 400:
                    raise ConnectionError("Error al crear la preferencia de pago, revise las credenciales.")
                preference = preference_response["response"]
                reserva.preference_id = preference["id"]
                reserva.save()
        return reserva

    def clean(self):
        cleaned_data = self.cleaned_data
        max_reservas_user = Parameters.objects.get(pk=1).max_reservas_user
        reservas = Reserva.objects.filter(email=self.data.get('email'))
        count = 0
        for reserva in reservas:
            if not reserva.is_finished():
                count += 1
        if count >= max_reservas_user:
            self._errors['email'] = self.error_class(
                ['El email ingresado ya tiene {} reservas pendientes de pago/activas, '
                 'no puede hacer más.'.format(max_reservas_user)])
            del cleaned_data['email']
        return cleaned_data

    class Meta:
        model = Reserva
        fields = ['cancha', 'fecha', 'hora', 'nota', 'nombre', 'email']
        widgets = {
            'cancha': forms.Select(attrs={'disabled': True}),
            'fecha': forms.DateInput(attrs={'class': 'form-control'}),
            'nota': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                          'placeholder': 'Ingrese una nota (opcional)'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su nombre'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su email'}),
        }
