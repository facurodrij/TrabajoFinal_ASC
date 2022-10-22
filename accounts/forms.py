from django import forms
# django admin
from django.contrib.admin.widgets import AdminFileWidget
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm, ReadOnlyPasswordHashField
from django.utils.translation import gettext_lazy as _

from .models import User, Persona


class CustomUserCreationForm(UserCreationForm):
    """
    Formulario para registrar un nuevo usuario.
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


class PersonaCreateForm(forms.ModelForm):
    """
    Formulario para registrar los datos personales
    de un Usuario o Miembro No Registrado.
    """
    dni = forms.CharField(max_length=9,
                          required=True,
                          label="DNI",
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
                                           attrs={
                                               'autocomplete': 'off',
                                               'placeholder': 'Fecha de nacimiento',
                                               'class': 'form-control  datetimepicker-input',
                                               'data-toggle': 'datetimepicker',
                                               'data-target': '#id_fecha_nacimiento',
                                           }
                                       ))
    localidad = forms.Select(attrs={'class': 'form-control'})
    direccion = forms.CharField(max_length=255,
                                required=True,
                                widget=forms.TextInput(attrs={'placeholder': 'Dirección',
                                                              'class': 'form-control',
                                                              }))
    imagen = forms.ImageField(required=True,
                              widget=AdminFileWidget)

    class Meta:
        model = Persona
        fields = ['dni', 'sexo', 'nombre', 'apellido', 'fecha_nacimiento', 'localidad', 'direccion', 'imagen']


class CustomAuthenticationForm(AuthenticationForm):
    """
    Formulario para iniciar sesión.
    """
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


class CustomUserChangeForm(UserChangeForm):
    """
    Formulario para actualizar los datos del modelo usuario.
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


class PersonaChangeForm(forms.ModelForm):
    """
    Formulario para actualizar los datos personales
    de un Usuario o Miembro No Registrado.
    """
    dni = forms.CharField(max_length=9,
                          required=True,
                          label="DNI",
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
                                           attrs={
                                               'autocomplete': 'off',
                                               'placeholder': 'Fecha de nacimiento',
                                               'class': 'form-control  datetimepicker-input',
                                               'data-toggle': 'datetimepicker',
                                               'data-target': '#id_fecha_nacimiento',
                                           }
                                       ))
    localidad = forms.Select(attrs={'class': 'form-control'})
    direccion = forms.CharField(max_length=255,
                                required=True,
                                widget=forms.TextInput(attrs={'placeholder': 'Dirección',
                                                              'class': 'form-control',
                                                              }))
    imagen = forms.ImageField(required=True,
                              widget=AdminFileWidget)

    class Meta:
        model = Persona
        fields = ['dni', 'sexo', 'nombre', 'apellido', 'fecha_nacimiento', 'localidad', 'direccion', 'imagen']
