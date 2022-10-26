from django import forms
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.admin.widgets import AdminFileWidget

from .models import Tipo, Socio, User, Persona, Categoria, Estado
from accounts.models import UsuarioPersona
from accounts.forms import PersonaForm
from core.models import Club
from parameters.models import Sexo, Localidad


# TODO: Crear un formulario para el modelo Categoria.
# TODO: Crear los formularios para crear un socio individual nuevo.
# TODO: Crear los formularios para crear un socio familiar nuevo.

class ElegirTipoForm(forms.Form):
    """
    Formulario para el paso 1 de una solicitud de asociación.
    """
    # Paso 1: Elegir el tipo de socio.
    tipo = forms.ModelChoiceField(required=True,
                                  queryset=Tipo.objects.all(),
                                  widget=forms.Select(attrs={'class': 'form-control select2'}))


class ElegirEstadoForm(forms.Form):
    """
    Formulario para elegir un estado de socio.
    """
    estado = forms.ModelChoiceField(required=True,
                                    queryset=Estado.objects.all(),
                                    widget=forms.Select(attrs={'class': 'form-control select2'}))


class BasicUserCreationForm(forms.ModelForm):
    """
    Formulario para la creación de un Usuario sin contraseña.
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

    class Meta:
        model = User
        fields = ('username', 'email')


# class MiembroRegistradoForm(forms.Form):
#     """
#     Formulario para la creación de un Usuario y una Persona.
#     """
#     username = BasicUserCreationForm['username']
#     email = BasicUserCreationForm['email']
#     dni = PersonaCreateForm['dni']
#     sexo = PersonaCreateForm['sexo']
#     nombre = PersonaCreateForm['nombre']
#     apellido = PersonaCreateForm['apellido']
#     fecha_nacimiento = PersonaCreateForm['fecha_nacimiento']
#     localidad = PersonaCreateForm['localidad']
#     direccion = PersonaCreateForm['direccion']
#     imagen = PersonaCreateForm['imagen']
#
#     # Validar que el username no exista.
#     def clean_username(self):
#         username = self.cleaned_data['username']
#         if User.objects.filter(username=username).exists():
#             raise ValidationError('El username {} ya existe.'.format(username))
#         return username
#
#     # Validar que el email no exista.
#     def clean_email(self):
#         email = self.cleaned_data['email']
#         if User.objects.filter(email=email).exists():
#             raise ValidationError('El email {} ya existe.'.format(email))
#         return email
#
#     # Validar que el dni no exista.
#     def clean_dni(self):
#         dni = self.cleaned_data['dni']
#         if Persona.objects.filter(dni=dni).exists():
#             raise ValidationError('El DNI {} ya existe.'.format(dni))
#         return dni
#
#     # Validar formulario.
#     def clean(self):
#         cleaned_data = super().clean()
#         username = cleaned_data.get('username')
#         email = cleaned_data.get('email')
#         dni = cleaned_data.get('dni')
#         sexo = cleaned_data.get('sexo')
#         nombre = cleaned_data.get('nombre')
#         apellido = cleaned_data.get('apellido')
#         fecha_nacimiento = cleaned_data.get('fecha_nacimiento')
#         localidad = cleaned_data.get('localidad')
#         direccion = cleaned_data.get('direccion')
#         imagen = cleaned_data.get('imagen')
#         if not username or not email or not dni or not nombre or not apellido or not fecha_nacimiento or not localidad \
#                 or not direccion or not imagen:
#             raise ValidationError('Complete todos los campos.')
#         self.clean_username()
#         self.clean_email()
#         self.clean_dni()
#         return cleaned_data
#
#     # Guardar formulario.
#     def save(self, commit=True):
#         self.clean()
#         # Crear usuario.
#         user = User(username=self.cleaned_data['username'],
#                     email=self.cleaned_data['email'],
#                     password=User.objects.make_random_password())
#         user.save(commit)
#         # Crear persona.
#         persona = Persona(dni=self.cleaned_data['dni'],
#                           sexo=self.cleaned_data['sexo'],
#                           nombre=self.cleaned_data['nombre'],
#                           apellido=self.cleaned_data['apellido'],
#                           fecha_nacimiento=self.cleaned_data['fecha_nacimiento'],
#                           localidad=self.cleaned_data['localidad'],
#                           direccion=self.cleaned_data['direccion'],
#                           imagen=self.cleaned_data['imagen'])
#         persona.save(commit)
#         # Crear relación usuario-persona.
#         usuario_persona = UsuarioPersona(usuario=user,
#                                          persona=persona)
#         usuario_persona.save(commit)
#         return user, persona, usuario_persona
