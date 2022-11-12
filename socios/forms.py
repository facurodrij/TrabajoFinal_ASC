from django import forms
from django.contrib.admin.widgets import AdminFileWidget
from django.core.exceptions import ValidationError

from accounts.models import User
from parameters.models import Parentesco
from socios.models import Estado, Categoria, Socio, Miembro, SolicitudSocio


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
                raise ValidationError('El miembro {} ya existe, pero se encuentra eliminado.'.format(miembro),
                                      code='miembro_exists_deleted')
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


class SolicitudForm(forms.ModelForm):
    """
    Formulario para crear una solicitud de socio.
    """
    dni = forms.CharField(max_length=8,
                          required=True,
                          widget=forms.TextInput(attrs={'placeholder': 'DNI',
                                                        'class': 'form-control',
                                                        }))
    email = forms.EmailField(required=True,
                             widget=forms.EmailInput(attrs={'placeholder': 'Email',
                                                            'class': 'form-control',
                                                            }))
    sexo = forms.Select(attrs={'class': 'form-control select2'})
    nombre = forms.CharField(max_length=100,
                             required=True,
                             widget=forms.TextInput(attrs={'placeholder': 'Nombre',
                                                           'class': 'form-control',
                                                           }))
    apellido = forms.CharField(max_length=100,
                               required=True,
                               widget=forms.TextInput(attrs={'placeholder': 'Apellido',
                                                             'class': 'form-control',
                                                             }))
    fecha_nacimiento = forms.DateField(required=True,
                                       widget=forms.DateInput(
                                           format='%d/%m/%Y',
                                           attrs={
                                               'autocomplete': 'off',
                                               'placeholder': 'Fecha de nacimiento',
                                               'class': 'form-control  datetimepicker-input',
                                               'data-toggle': 'datetimepicker',
                                               'data-target': '#id_fecha_nacimiento',
                                           }
                                       ))
    imagen = forms.ImageField(required=True, widget=AdminFileWidget)

    def clean(self):
        super(SolicitudForm, self).clean()
        dni = self.cleaned_data['dni']
        try:
            solicitud = SolicitudSocio.objects.get(dni=dni)
            raise ValidationError('Ya existe una solicitud enviada con el DNI ingresado. '
                                  'Estado de solicitud: {}'.format(solicitud.get_estado()))
        except SolicitudSocio.DoesNotExist:
            pass
        try:
            Socio.global_objects.get(persona__dni=dni)
            raise ValidationError('Ya existe un socio con el DNI ingresado. Por favor, verifique los datos ingresados.')
        except Socio.DoesNotExist:
            pass
        email = self.cleaned_data['email']
        try:
            User.global_objects.get(email=email)
            raise ValidationError('Ya existe un usuario con el email ingresado. '
                                  'Por favor, verifique los datos ingresados.')
        except User.DoesNotExist:
            pass

    class Meta:
        model = SolicitudSocio
        fields = ['nombre', 'apellido', 'dni', 'email', 'sexo', 'fecha_nacimiento', 'imagen', 'categoria']
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-control select2'}),
        }
