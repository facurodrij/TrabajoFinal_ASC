from django import forms

from .models import Club


class ClubForm(forms.ModelForm):
    class Meta:
        model = Club
        fields = ['nombre', 'localidad', 'direccion', 'logo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'localidad': forms.Select(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección'}),
            'logo': forms.FileInput(attrs={'class': 'form-control-file'}),
        }
        labels = {
            'nombre': 'Nombre',
            'pais': 'País',
            'provincia': 'Provincia',
            'localidad': 'Localidad',
            'direccion': 'Dirección',
            'logo': 'Logo',
        }
