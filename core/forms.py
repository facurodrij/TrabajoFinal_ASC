from django import forms

from .models import Club


class ClubForm(forms.ModelForm):
    class Meta:
        model = Club
        fields = ['nombre', 'localidad', 'direccion', 'logo', 'administrador']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'localidad': forms.Select(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección'}),
            'logo': forms.FileInput(attrs={'class': 'form-control-file'}),
            'administrador': forms.SelectMultiple(attrs={'class': 'form-control input-sm select2-multiple'}),
        }
        labels = {
            'nombre': 'Nombre',
            'pais': 'País',
            'provincia': 'Provincia',
            'localidad': 'Localidad',
            'direccion': 'Dirección',
            'logo': 'Logo',
        }
