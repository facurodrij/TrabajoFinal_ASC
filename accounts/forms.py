from django import forms
from django.contrib.admin.widgets import AdminFileWidget
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm, ReadOnlyPasswordHashField
from django.utils.translation import gettext_lazy as _

from .models import User, Persona


class CreateUserFormAdmin(UserCreationForm):
    """
    Formulario para registrar un nuevo usuario. Se utiliza en el panel de administrador.
    """
    username = forms.CharField(max_length=100,
                               required=True,
                               widget=forms.TextInput(attrs={'placeholder': 'Username',
                                                             'class': 'form-control',
                                                             }))
    email = forms.EmailField(required=True,
                             widget=forms.TextInput(attrs={'placeholder': 'Email',
                                                           'class': 'form-control',
                                                           }))
    password1 = forms.CharField(max_length=50,
                                label='Contraseña',
                                required=True,
                                widget=forms.PasswordInput(attrs={'placeholder': 'Contraseña',
                                                                  'class': 'form-control',
                                                                  'data-toggle': 'password',
                                                                  }))
    password2 = forms.CharField(max_length=50,
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
    Formulario para registrar un nuevo usuario. Solamente con el Email es sufiiciente.
    El resto de datos obligatorios se completan en la vista que lo utiliza.
    """
    add_user = forms.BooleanField(required=False)
    email = forms.EmailField(required=False,
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
    username = forms.CharField(max_length=150,
                               required=True,
                               widget=forms.TextInput(attrs={'placeholder': 'Username',
                                                             'class': 'form-control',
                                                             }))
    email = forms.EmailField(required=True,
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
    dni = forms.CharField(max_length=8,
                          required=True,
                          widget=forms.TextInput(attrs={'placeholder': 'DNI',
                                                        'class': 'form-control',
                                                        }))
    sexo = forms.Select(attrs={'class': 'form-control select2'})
    nombre = forms.CharField(max_length=100,
                             required=True,
                             widget=forms.TextInput(attrs={'placeholder': 'Nombre',
                                                           'class': 'form-control',
                                                           }))
    apellido = forms.CharField(max_length=100,
                               required=True,
                               widget=forms.TextInput(attrs={'placeholder': 'Apellido',
                                                             'class': 'form-control',
                                                             }))
    fecha_nacimiento = forms.DateField(required=True,
                                       widget=forms.DateInput(
                                           format='%d/%m/%Y',
                                           attrs={
                                               'autocomplete': 'off',
                                               'placeholder': 'Fecha de nacimiento',
                                               'class': 'form-control  datetimepicker-input',
                                               'data-toggle': 'datetimepicker',
                                               'data-target': '#id_fecha_nacimiento',
                                           }
                                       ))
    imagen = forms.ImageField(required=True, widget=AdminFileWidget)

    class Meta:
        model = Persona
        exclude = ['club']


class LoginForm(AuthenticationForm):
    username = forms.CharField(max_length=100,
                               required=True,
                               widget=forms.TextInput(attrs={'placeholder': 'Username',
                                                             'class': 'form-control',
                                                             }))
    password = forms.CharField(max_length=50,
                               required=True,
                               widget=forms.PasswordInput(attrs={'placeholder': 'Contraseña',
                                                                 'class': 'form-control',
                                                                 'data-toggle': 'password',
                                                                 'id': 'password',
                                                                 'name': 'password',
                                                                 }))
    remember_me = forms.BooleanField(required=False, label='Recordarme')

    class Meta:
        model = User
        fields = ['username', 'password', 'remember_me']


class SignUpForm(forms.Form):
    """
    Formulario para que un socio sin usuario pueda registrarse.
    Debe pasar su DNI para comprobar si existe en la tabla Persona y está asociado
    con la tabla Socio; y un Email personal.
    """
    dni = forms.CharField(max_length=8,
                          required=True,
                          widget=forms.TextInput(attrs={'placeholder': 'DNI',
                                                        'class': 'form-control',
                                                        }))
    email = forms.EmailField(required=True,
                             widget=forms.TextInput(attrs={'placeholder': 'Email',
                                                           'class': 'form-control',
                                                           }))

    def clean_email(self):
        """
        Validar que el Email no exista en otro Usuario.
        """
        email = self['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('El Email ingresado ya está registrado.')
        return email

    def clean_dni(self):
        """
        Validar que el DNI exista en la tabla Persona y esté asociado con la tabla Socio.
        """
        dni = self['dni']
        if not Socio.objects.filter(persona__dni=dni).exists():
            raise forms.ValidationError('El DNI ingresado no pertenece a un socio del Club. '
                                        'Para registrarse debe ser socio.')
        return dni
