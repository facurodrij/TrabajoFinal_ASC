from django.contrib import messages
from django.shortcuts import redirect


def socio_required(function):
    def wrap(request, *args, **kwargs):
        try:
            if not request.user.is_socio() and not request.user.is_admin():
                messages.error(request, 'Primero debes rellenar la solicitud de asociación')
                return redirect('asociarse')
        except AttributeError:
            pass
        return function(request, *args, **kwargs)

    wrap.__doc__ = function.__doc__
    wrap.__name__ = function.__name__
    return wrap
