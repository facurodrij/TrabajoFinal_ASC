from django import forms

from socios.models import Categoria, Socio, CuotaSocial, Parameters


class SocioAdminForm(forms.ModelForm):
    """
    Formulario para crear un socio.
    """
    persona = forms.Select()
    user = forms.CharField(required=False,
                           label='Usuario',
                           widget=forms.TextInput(attrs={'readonly': 'readonly',
                                                         'class': 'form-control'}))
    email = forms.EmailField(required=False,
                             label='Email',
                             widget=forms.EmailInput(attrs={'class': 'form-control',
                                                            'placeholder': 'Ingrese el email'}))

    class Meta:
        model = Socio
        fields = ['persona']


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


class SocioParametersForm(forms.ModelForm):
    """Formulario para la edición de los parámetros de socios."""

    class Meta:
        model = Parameters
        fields = '__all__'
        widgets = {
            'club': forms.HiddenInput(),
            'edad_minima_titular': forms.NumberInput(attrs={'class': 'form-control'}),
            'dia_emision_cuota': forms.NumberInput(attrs={'class': 'form-control'}),
            'dia_vencimiento_cuota': forms.NumberInput(attrs={'class': 'form-control'}),
            'cantidad_maxima_cuotas_pendientes': forms.NumberInput(attrs={'class': 'form-control'}),
            'aumento_por_cuota_vencida': forms.NumberInput(attrs={'class': 'form-control'}),
        }
