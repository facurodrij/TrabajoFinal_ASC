from django import forms

from core.models import Club, Reserva, HoraLaboral


class UpdateClubForm(forms.ModelForm):
    """Formulario para actualizar el club."""
    nombre = forms.CharField(max_length=100,
                             required=True,
                             widget=forms.TextInput(attrs={'class': 'form-control'}))
    localidad = forms.Select(attrs={'class': 'form-control'})
    direccion = forms.CharField(max_length=100,
                                required=True,
                                widget=forms.TextInput(attrs={'class': 'form-control'}))
    logo = forms.ImageField(required=False,
                            widget=forms.FileInput(attrs={'class': 'form-control-file'}))

    class Meta:
        model = Club
        fields = ['nombre', 'localidad', 'direccion', 'imagen']


class ReservaAdminForm(forms.ModelForm):
    """Formulario para crear una reserva."""
    hora = forms.ModelChoiceField(
        queryset=HoraLaboral.objects.all(),
        widget=forms.Select())

    class Meta:
        model = Reserva
        fields = ['cancha', 'nombre', 'email', 'fecha', 'nota', 'is_pagado']
        widgets = {
            'cancha': forms.Select(attrs={'disabled': True}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el nombre'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el email'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control'}),
            'nota': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_pagado': forms.CheckboxInput(),
        }
