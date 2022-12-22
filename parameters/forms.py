from django import forms

from parameters.models import ClubParameters


class ParametersClubForm(forms.ModelForm):
    """Formulario para la edición de los parámetros de socios."""

    class Meta:
        model = ClubParameters
        fields = '__all__'
        widgets = {
            'club': forms.HiddenInput(),
            'edad_minima_titular': forms.NumberInput(attrs={'class': 'form-control'}),
            'dia_emision_cuota': forms.NumberInput(attrs={'class': 'form-control'}),
            'dia_vencimiento_cuota': forms.NumberInput(attrs={'class': 'form-control'}),
            'cantidad_maxima_cuotas_pendientes': forms.NumberInput(attrs={'class': 'form-control'}),
            'aumento_por_cuota_vencida': forms.NumberInput(attrs={'class': 'form-control'}),
        }