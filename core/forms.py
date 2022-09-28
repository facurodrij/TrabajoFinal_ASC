from django import forms

from .models import Club


class ClubForm(forms.ModelForm):
    class Meta:
        model = Club
        fields = ['nombre', 'pais', 'provincia', 'localidad', 'direccion', 'logo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'pais': forms.Select(attrs={'class': 'form-control'}),
            'provincia': forms.Select(attrs={'class': 'form-control'}),
            'localidad': forms.Select(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
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
