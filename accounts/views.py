from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import (
    REDIRECT_FIELD_NAME, get_user_model, login as auth_login,
    logout as auth_logout, update_session_auth_hash,
)
from django.utils.safestring import mark_safe

from .models import UsuarioPersona
from .forms import *
from .decorators import no_login_required


class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
    sucess_url = reverse_lazy('index')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Login'
        return context

    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')
        if not remember_me:
            # set session expiry to 0 seconds. So it will automatically close the session after the browser is closed.
            self.request.session.set_expiry(0)
            # Set session as modified to force data updates/cookie to be saved.
            self.request.session.modified = True
        """Security check complete. Log the user in."""
        auth_login(self.request, form.get_user())
        try:
            # Si inicia sesión un socio con estado inactivo, se le redirige al logout.
            if not self.request.user.socioindividual.estado.is_active:
                messages.error(self.request, 'Socio inactivo. ' + self.request.user.socioindividual.estado.descripcion)
                return redirect('logout')
        except ObjectDoesNotExist:
            # Si inicia sesión un socio que no tiene relación con SocioIndividual y no es administrador,
            # se le redirige al logout.
            if not self.request.user.is_admin():
                messages.error(self.request, mark_safe(
                    'Su Usuario existe pero no pertenece a un Socio del club.'
                    + '<br/>'
                    + 'Por favor contacte con el club para solucionar el problema.'))
                return redirect('logout')
            pass
        return super(CustomLoginView, self).form_valid(form)


@login_required
@permission_required('accounts.change_persona', raise_exception=True)
def persona(request):
    """
    Vista para los datos personales del usuario.
    """
    try:
        UsuarioPersona.objects.get(user=request.user)
    except UsuarioPersona.DoesNotExist:
        messages.error(request, 'Su usuario no tiene relación con la tabla persona, por ende no puede ver el sitio.')
        return redirect('index')

    context = {
        'title': 'Datos Personales',
    }
    if request.method == 'POST':
        user_form = CustomUserChangeForm(request.POST, instance=request.user)
        persona_form = PersonaChangeForm(request.POST, request.FILES, instance=request.user.usuariopersona.persona)

        if user_form.is_valid() and persona_form.is_valid():
            user_form.save()
            persona_form.save()
            messages.success(request, 'Datos Personales actualizados exitosamente')
            return redirect(to='persona')
    else:
        user_form = CustomUserChangeForm(instance=request.user)
        persona_form = PersonaChangeForm(instance=request.user.usuariopersona.persona)

    return render(request, 'persona.html', {'user_form': user_form, 'persona_form': persona_form, **context})
