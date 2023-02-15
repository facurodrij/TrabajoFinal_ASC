from django import forms
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.forms import UserCreationForm, UsernameField, AuthenticationForm
from django.utils.translation import gettext_lazy as _

from accounts.models import User


class LoginForm(AuthenticationForm):
    """
    Formulario para el login de usuarios.
    """
    username_field = User._meta.get_field(User.USERNAME_FIELD)
    username = UsernameField(
        max_length=100,
        widget=forms.EmailInput(
            attrs={
                'autofocus': True,
                'class': 'form-control',
                'placeholder': 'Ingrese su email',
                'autocomplete': 'off',
            }
        )
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password",
                                          'class': 'form-control',
                                          'placeholder': 'Contraseña'}),
    )
    remember_me = forms.BooleanField(
        required=False, label='Recordarme')

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(self.request, email=username, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )
            else:
                self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class SignUpForm(UserCreationForm):
    """
    Formulario para el registro de usuarios.
    """
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password",
                                          'class': 'form-control',
                                          'placeholder': 'Contraseña'}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password",
                                          'class': 'form-control',
                                          'placeholder': 'Repetir contraseña'}),
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nombre'].widget.attrs['autofocus'] = True

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.is_active = False
        if commit:
            user.save()
        return user

    class Meta:
        model = User
        fields = ('email', 'nombre', 'apellido', 'notificaciones')
        field_classes = {'email': UsernameField}
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'Ingrese su email',
                                             'class': 'form-control',
                                             'autocomplete': 'off',
                                             }),
            'nombre': forms.TextInput(attrs={'placeholder': 'Ingrese su nombre',
                                             'class': 'form-control',
                                             'autocomplete': 'off',
                                             }),
            'apellido': forms.TextInput(attrs={'placeholder': 'Ingrese su apellido',
                                               'class': 'form-control',
                                               'autocomplete': 'off',
                                               }),
            'notificaciones': forms.CheckboxInput(),
        }


class ProfileForm(forms.ModelForm):
    """
    Formulario para el perfil de usuarios.
    """
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password",
                                          'class': 'form-control',
                                          'placeholder': 'Contraseña actual'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nombre'].widget.attrs['autofocus'] = True

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not self.instance.check_password(password):
            raise forms.ValidationError('Contraseña incorrecta')
        pass

    class Meta:
        model = User
        fields = ('nombre', 'apellido', 'notificaciones')
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ingrese su nombre',
                                             'class': 'form-control',
                                             'autocomplete': 'off',
                                             }),
            'apellido': forms.TextInput(attrs={'placeholder': 'Ingrese su apellido',
                                               'class': 'form-control',
                                               'autocomplete': 'off',
                                               }),
            'notificaciones': forms.CheckboxInput(),
        }


class ChangeEmailForm(forms.ModelForm):
    """
    Formulario para el cambio de email de usuarios.
    """
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password",
                                          'class': 'form-control',
                                          'placeholder': 'Contraseña actual'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs['autofocus'] = True

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not self.instance.check_password(password):
            raise forms.ValidationError('Contraseña incorrecta')
        pass

    class Meta:
        model = User
        fields = ('email',)
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'Ingrese su nuevo email',
                                             'class': 'form-control',
                                             'autocomplete': 'off',
                                             }),
        }
