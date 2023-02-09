import mercadopago
from django import forms
from django.db import OperationalError, ProgrammingError

from core.models import Club, Persona
from socios.models import Parameters
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
    imagen = forms.ImageField(required=False,
                            widget=forms.FileInput(attrs={'class': 'custom-file-input'}))

    def clean_imagen(self):
        imagen = self.cleaned_data['imagen']
        if imagen == self.instance.imagen:
            return self.instance.imagen
        return imagen

    class Meta:
        model = Club
        fields = ['nombre', 'localidad', 'direccion', 'imagen']


class PersonaAdminForm(forms.ModelForm):
    """
    Formulario para registrar los datos de una Persona. Se utiliza en el formulario de registro de un nuevo usuario.
    """
    try:
        edad_minima_titular = Parameters.objects.get(club_id=1).edad_minima_titular
        es_menor = forms.BooleanField(
            label='Es menor de {} años?'.format(edad_minima_titular),
            required=False,
            widget=forms.CheckboxInput(),
            help_text='Marque esta casilla si la persona es menor de {} años.'.format(edad_minima_titular)
        )
    except (OperationalError, ProgrammingError, Parameters.DoesNotExist) as e:
        es_menor = forms.BooleanField(
            label='Es menor?',
            required=False,
            widget=forms.CheckboxInput(),
            help_text='Marque esta casilla si la persona es menor.'
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
    persona_titular = forms.ModelChoiceField(
        required=False,
        label='Persona a cargo',
        help_text='Seleccione la persona a cargo.',
        queryset=Persona.objects.filter(persona_titular__isnull=True),
        widget=forms.Select())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['club'].initial = Club.objects.get(pk=1)

    class Meta:
        model = Persona
        fields = ['cuil', 'sexo', 'nombre', 'apellido', 'fecha_nacimiento', 'imagen', 'club', 'persona_titular']
        widgets = {
            'sexo': forms.Select(),
            'nombre': forms.TextInput(attrs={'placeholder': 'Ingrese el nombre',
                                             'class': 'form-control',
                                             'autocomplete': 'off',
                                             }),
            'apellido': forms.TextInput(attrs={'placeholder': 'Ingrese el apellido',
                                               'class': 'form-control',
                                               'autocomplete': 'off',
                                               }),
            'fecha_nacimiento': forms.TextInput(attrs={'placeholder': 'Ingrese la fecha de nacimiento',
                                                       'class': 'form-control',
                                                       'autocomplete': 'off',
                                                       }),
            'imagen': forms.FileInput(attrs={'class': 'custom-file-input'}),
            'club': forms.HiddenInput(),
        }