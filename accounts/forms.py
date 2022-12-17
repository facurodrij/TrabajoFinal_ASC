from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from accounts.models import User, Persona
from socios.models import Socio


class CreateUserFormAdmin(UserCreationForm):
    """
    Formulario para registrar un nuevo usuario. Se utiliza en el panel de administrador.
    """
    username = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Username',
                                      'class': 'form-control',
                                      }))
    email = forms.EmailField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Email',
                                      'class': 'form-control',
                                      }))
    password1 = forms.CharField(
        max_length=50,
        label='Contraseña',
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Contraseña',
                                          'class': 'form-control',
                                          'data-toggle': 'password',
                                          }))
    password2 = forms.CharField(
        max_length=50,
        label='Confirmar contraseña',
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirmar contraseña',
                                          'class': 'form-control',
                                          'data-toggle': 'password',
                                          }))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class SimpleCreateUserForm(forms.Form):
    """
    Formulario para registrar un nuevo usuario. Solamente con el Email es suficiente.
    El resto de datos obligatorios se completan en la vista que lo utiliza.
    """
    add_user = forms.BooleanField(required=False)
    email = forms.EmailField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Email',
                                      'class': 'form-control',
                                      }))

    # Validad el campo email, que sea unico.
    def clean_email(self):
        email = self['email'].value()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('El email ya existe.')
        return email


class UpdateUserFormAdmin(UserChangeForm):
    """
    Formulario para actualizar los datos del modelo usuario. Se utiliza en el panel de administrador.
    """
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Username',
                                      'class': 'form-control',
                                      }))
    email = forms.EmailField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Email',
                                      'class': 'form-control',
                                      }))

    class Meta:
        model = User
        fields = ['username', 'email']


class PersonaFormAdmin(forms.ModelForm):
    """
    Formulario para registrar los datos de una Persona. Se utiliza en el formulario de registro de un nuevo usuario.
    """
    dni = forms.CharField(
        max_length=8,
        label='DNI',
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Ingrese su DNI',
                                      'class': 'form-control',
                                      'autocomplete': 'off',
                                      }))
    sexo = forms.Select(attrs={'class': 'form-control select2'})
    nombre = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Ingrese su nombre',
                                      'class': 'form-control',
                                      'autocomplete': 'off',
                                      }))
    apellido = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Ingrese su apellido',
                                      'class': 'form-control',
                                      'autocomplete': 'off',
                                      }))
    fecha_nacimiento = forms.DateField(
        required=True,
        widget=forms.TextInput(
            attrs={
                'autocomplete': 'off',
                'placeholder': 'Ingrese su fecha de nacimiento',
                'class': 'form-control  datetimepicker-input',
                'data-toggle': 'datetimepicker',
                'data-target': '#id_fecha_nacimiento',
            }
        ))
    imagen = forms.ImageField(
        required=True,
        label='Foto carnet',
        widget=forms.FileInput(
            attrs={
                'class': 'custom-file-input',
            }
        ))

    class Meta:
        model = Persona
        exclude = ['club']


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
    dni = forms.CharField(
        max_length=8,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'DNI',
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

    def clean_dni(self):
        """
        Validar que el DNI exista en la tabla Persona y esté asociado con la tabla Socio.
        """
        dni = self['dni'].value()
        if not Socio.objects.filter(persona__dni=dni).exists():
            raise forms.ValidationError('El DNI ingresado no pertenece a un socio del Club. '
                                        'Para registrarse debe ser socio.')
        # Validar que el dni no este asociado a un usuario.
        if User.objects.filter(persona__dni=dni).exists():
            raise forms.ValidationError('El DNI ingresado ya está registrado.')
        return dni

    def clean_socio_id(self):
        """
        Validar que el socio_id exista en la tabla Socio y coincida con el DNI ingresado.
        """
        socio_id = self['socio_id'].value()
        dni = self['dni'].value()
        if not Socio.objects.filter(id=socio_id, persona__dni=dni).exists():
            raise forms.ValidationError('El número de Socio ingresado no coincide con el DNI ingresado.')
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
