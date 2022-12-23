from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from accounts.models import User, Persona
from core.models import Club
from parameters.models import ClubParameters
from socios.models import Socio


class PersonaAdminForm(forms.ModelForm):
    """
    Formulario para registrar los datos de una Persona. Se utiliza en el formulario de registro de un nuevo usuario.
    """
    edad_minima_titular = ClubParameters.objects.get(club_id=1).edad_minima_titular
    es_menor = forms.BooleanField(
        label='Es menor de {} años?'.format(edad_minima_titular),
        required=False,
        # Clase de bootstrap para alinear a la izquierda centrado verticalmente el checkbox.
        widget=forms.CheckboxInput(attrs={'class': 'ml-1 mt-2'}),
        help_text='Marque esta casilla si la persona es menor de {} años.'.format(edad_minima_titular)
    )
    cuil = forms.CharField(
        max_length=13,
        label='CUIL',
        required=True,
        widget=forms.TextInput(
            attrs={'placeholder': '00-00000000-0',
                   'class': 'form-control',
                   'autocomplete': 'off',
                   }))
    sexo = forms.Select(attrs={'class': 'form-control select2'})
    persona_titular = forms.ModelChoiceField(
        required=False,
        label='Persona a cargo',
        queryset=Persona.objects.filter(persona_titular__isnull=True),
        widget=forms.Select(attrs={'class': 'form-control select2'}))
    nombre = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={'placeholder': 'Ingrese el nombre',
                   'class': 'form-control',
                   'autocomplete': 'off',
                   }))
    apellido = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={'placeholder': 'Ingrese el apellido',
                   'class': 'form-control',
                   'autocomplete': 'off',
                   }))
    fecha_nacimiento = forms.DateField(
        required=True,
        widget=forms.TextInput(
            attrs={
                'autocomplete': 'off',
                'placeholder': 'Ingrese la fecha de nacimiento',
                'class': 'form-control datetimepicker-input',
                'data-toggle': 'datetimepicker',
                'data-target': '#id_fecha_nacimiento',
            }
        ))
    imagen = forms.ImageField(
        required=True,
        label='Foto carnet',
        widget=forms.FileInput(attrs={'class': 'custom-file-input'}))
    club = forms.ModelChoiceField(
        queryset=Club.objects.all(),
        widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['club'].initial = Club.objects.get(pk=1)

    class Meta:
        model = Persona
        fields = ['cuil', 'sexo', 'nombre', 'apellido', 'fecha_nacimiento', 'imagen', 'club']


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Username',
                                      'class': 'form-control',
                                      'autocomplete': 'off',
                                      }))
    password = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Contraseña',
                                          'class': 'form-control',
                                          'data-toggle': 'password',
                                          'id': 'password',
                                          'name': 'password',
                                          }))
    remember_me = forms.BooleanField(
        required=False, label='Recordarme')

    class Meta:
        model = User
        fields = ['username', 'password', 'remember_me']


class SignUpForm(forms.Form):
    """
    Formulario para que un socio sin usuario pueda registrarse.
    Debe pasar su DNI para comprobar si existe en la tabla Persona y está asociado
    con la tabla Socio; y un Email personal.
    """
    cuil = forms.CharField(
        max_length=13,
        label='CUIL',
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Ingrese el CUIL',
                                      'class': 'form-control',
                                      'autocomplete': 'off',
                                      }))
    email = forms.EmailField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Email',
                                      'class': 'form-control',
                                      'autocomplete': 'off',
                                      }))
    socio_id = forms.IntegerField(required=True,
                                  widget=forms.NumberInput(attrs={'class': 'form-control',
                                                                  'placeholder': 'Socio ID',
                                                                  'autocomplete': 'off',
                                                                  }))
    error_messages = {
        "password_mismatch": _("The two password fields didn’t match."),
    }
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password",
                                          'placeholder': 'Contraseña',
                                          'class': 'form-control'
                                          }),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password",
                                          'placeholder': 'Confirmar contraseña',
                                          'class': 'form-control'}),
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )

    def clean_email(self):
        """
        Validar que el Email no exista en otro Usuario.
        """
        email = self['email'].value()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('El Email ingresado ya está registrado.')
        return email

    def clean_cuil(self):
        """
        Validar que el CUIL exista en la tabla Persona y esté asociado con la tabla Socio.
        """
        cuil = self['cuil'].value()
        if not Socio.objects.filter(persona__cuil=cuil).exists():
            raise forms.ValidationError('El CUIL ingresado no pertenece a un socio del Club. '
                                        'Para registrarse debe ser socio.')
        # Validar que el cuil no este asociado a un usuario.
        if User.objects.filter(persona__cuil=cuil).exists():
            raise forms.ValidationError('El CUIL ingresado ya está registrado.')
        return cuil

    def clean_socio_id(self):
        """
        Validar que el socio_id exista en la tabla Socio y coincida con el CUIL ingresado.
        """
        socio_id = self['socio_id'].value()
        cuil = self['cuil'].value()
        if not Socio.objects.filter(id=socio_id, persona__cuil=cuil).exists():
            raise forms.ValidationError('El número de Socio ingresado no coincide con el CUIL ingresado.')
        return socio_id

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError(
                self.error_messages["password_mismatch"],
                code="password_mismatch",
            )
        return password2

    def _post_clean(self):
        super()._post_clean()
        # Validate the password after self.instance is updated with form data
        # by super().
        password = self.cleaned_data.get("password2")
        if password:
            try:
                password_validation.validate_password(password)
            except ValidationError as error:
                self.add_error("password2", error)
