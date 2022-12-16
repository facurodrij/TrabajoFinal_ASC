from datetime import date

from dateutil import relativedelta
from django import forms

from accounts.models import Persona
from parameters.models import Parentesco, ClubParameters
from socios.models import Categoria, Socio, CuotaSocial


class SelectCategoriaForm(forms.Form):
    """
    Formulario para elegir una categoria de socio.
    """
    categoria = forms.ModelChoiceField(required=True,
                                       queryset=Categoria.objects.all(),
                                       widget=forms.Select(attrs={'class': 'form-control select2'}))


class SelectParentescoForm(forms.Form):
    """
    Formulario para elegir un parentesco.
    """
    parentesco = forms.ModelChoiceField(required=True,
                                        queryset=Parentesco.objects.all(),
                                        widget=forms.Select(attrs={'class': 'form-control select2'}))


class SocioForm(forms.ModelForm):
    """
    Formulario para crear un socio.
    """
    edad_minima_titular = ClubParameters.objects.get(club_id=1).edad_minima_socio_titular
    persona = forms.ModelChoiceField(required=True,
                                     # Queryset de personas que no son socios y su edad es
                                     # mayor a la edad minima de socio titular.
                                     queryset=Persona.objects.filter(socio__isnull=True).filter(
                                         fecha_nacimiento__lte=date.today() - relativedelta.relativedelta(
                                             years=edad_minima_titular)),
                                     widget=forms.Select(attrs={'class': 'form-control select2'}))
    socio_titular = forms.ModelChoiceField(required=False,
                                           queryset=Socio.global_objects.all().filter(socio_titular__isnull=True),
                                           widget=forms.Select(attrs={'class': 'form-control select2'}))
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

    class Meta:
        model = Socio
        fields = ['persona', 'categoria', 'socio_titular', 'parentesco', 'fecha_ingreso']
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-control select2'}),
            'parentesco': forms.Select(attrs={'class': 'form-control select2'}),
        }


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
