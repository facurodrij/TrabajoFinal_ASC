from django.contrib import messages
from django.shortcuts import redirect


def socio_required(function):
    def wrap(request, *args, **kwargs):
        try:
            if not request.user.persona.get_socio() and not request.user.is_admin():
                messages.error(request, 'Debes ser socio del club para acceder a esta sección.')
                return redirect('asociarse')
        except AttributeError:
            pass
        return function(request, *args, **kwargs)

    wrap.__doc__ = function.__doc__
    wrap.__name__ = function.__name__
    return wrap
