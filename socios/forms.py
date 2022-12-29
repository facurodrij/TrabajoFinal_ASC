from django import forms

from accounts.models import Persona
from socios.models import Categoria, Socio, CuotaSocial


class SocioAdminForm(forms.ModelForm):
    """
    Formulario para crear un socio.
    """
    persona = forms.Select(attrs={'class': 'form-control select2'})
    user = forms.CharField(required=False,
                           label='Usuario',
                           widget=forms.TextInput(attrs={'readonly': 'readonly',
                                                         'class': 'form-control'}))
    email = forms.EmailField(required=False,
                             label='Email',
                             widget=forms.EmailInput(attrs={'class': 'form-control',
                                                            'placeholder': 'Ingrese el email'}))
    fecha_ingreso = forms.DateField(
        required=True,
        widget=forms.TextInput(
            attrs={
                'autocomplete': 'off',
                'placeholder': 'Fecha de ingreso',
                'class': 'form-control  datetimepicker-input',
                'data-toggle': 'datetimepicker',
                'data-target': '#id_fecha_ingreso',
            }
        ))

    # user toma el valor del socio
    def __init__(self, *args, **kwargs):
        super(SocioAdminForm, self).__init__(*args, **kwargs)
        self.fields['user'].initial = self.instance.get_user().email if self.instance.get_user() else None

    class Meta:
        model = Socio
        fields = ['persona', 'fecha_ingreso']


class CuotaSocialForm(forms.ModelForm):
    """
    Formulario para crear una cuota social.
    """
    con_vencimiento = forms.BooleanField(required=False,
                                         widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    meses = forms.MultipleChoiceField(required=True,
                                      choices=CuotaSocial.MESES,
                                      widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': '12'}))

    class Meta:
        model = CuotaSocial
        fields = ['persona', 'periodo_anio', 'cargo_extra', 'observaciones']
        widgets = {
            'persona': forms.HiddenInput(),
            # 'periodo_mes': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '12'}),
            'periodo_anio': forms.DateTimeInput(attrs={'class': 'form-control'}),
            'cargo_extra': forms.NumberInput(attrs={'class': 'form-control', 'value': 0}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class CategoriaForm(forms.ModelForm):
    """
    Formulario para crear una categoria de socio.
    """

    class Meta:
        model = Categoria
        fields = ['nombre', 'cuota', 'edad_minima', 'edad_maxima']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el nombre'}),
            'cuota': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el monto de la cuota'}),
            'edad_minima': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese la edad minima'}),
            'edad_maxima': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese la edad maxima'}),
        }
