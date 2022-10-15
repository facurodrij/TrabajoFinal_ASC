from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.views import LoginView

from .models import UsuarioPersona
from .forms import *
from .decorators import no_login_required


@no_login_required
def register(request):
    """
    Vista para registrar un nuevo usuario.
    """
    context = {
        'title': 'Registro',
    }
    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST)
        persona_form = PersonaCreateForm(request.POST)
        if user_form.is_valid() and persona_form.is_valid():
            user = user_form.save()
            persona = persona_form.save()
            UsuarioPersona.objects.create(user=user, persona=persona)
            messages.success(request, 'Usuario registrado correctamente.')
            return redirect('login')
    else:
        user_form = CustomUserCreationForm()
        persona_form = PersonaCreateForm()
    return render(request, 'registration/register.html',
                  {'user_form': user_form, 'persona_form': persona_form, **context})


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

        # else browser session will be as long as the session cookie time "SESSION_COOKIE_AGE" defined in settings.py
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
