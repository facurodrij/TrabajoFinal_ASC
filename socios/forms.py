from django import forms
from django.db import IntegrityError
from django.contrib.admin.widgets import AdminFileWidget
from django.core.exceptions import ValidationError

from socios.models import Estado, Categoria, Socio, Miembro
from parameters.models import Parentesco


class SelectEstadoForm(forms.Form):
    """
    Formulario para elegir un estado de socio.
    """
    estado = forms.ModelChoiceField(required=True,
                                    queryset=Estado.objects.all(),
                                    widget=forms.Select(attrs={'class': 'form-control select2'}))


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
    # Validar si el socio que se quiere crear ya existe y está eliminado
    def clean(self):
        super(SocioForm, self).clean()
        try:
            socio = Socio.global_objects.get(persona_id=self.cleaned_data['persona'])
            if socio.is_deleted:
                raise ValidationError('El socio {} ya existe, pero se encuentra eliminado.'.format(socio))
        except Socio.DoesNotExist:
            pass

    class Meta:
        model = Socio
        fields = ['persona', 'categoria', 'estado']
        widgets = {
            'persona': forms.Select(attrs={'class': 'form-control select2'}),
            'categoria': forms.Select(attrs={'class': 'form-control select2'}),
            'estado': forms.Select(attrs={'class': 'form-control select2'}),
        }


class MiembroForm(forms.ModelForm):
    """
    Formulario para crear un miembro.
    """
    # Validar si el miembro que se quiere crear ya existe y está eliminado
    def clean(self):
        super(MiembroForm, self).clean()
        try:
            miembro = Miembro.global_objects.get(persona_id=self.cleaned_data['persona'])
            if miembro.is_deleted:
                raise ValidationError('El miembro {} ya existe, pero se encuentra eliminado.'.format(miembro))
        except Miembro.DoesNotExist:
            pass

    class Meta:
        model = Miembro
        fields = ['socio', 'persona', 'parentesco', 'categoria']
        widgets = {
            'socio': forms.Select(attrs={'class': 'form-control select2'}),
            'persona': forms.Select(attrs={'class': 'form-control select2'}),
            'parentesco': forms.Select(attrs={'class': 'form-control select2'}),
            'categoria': forms.Select(attrs={'class': 'form-control select2'}),
        }
