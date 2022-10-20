from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.shortcuts import redirect


def no_login_required(function=None, redirect_field_name=None, login_url='index'):
    """
    Decorator for views that checks that the user is not logged in, redirecting
    to the index if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: not u.is_authenticated,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def admin_required(function):
    def wrap(request, *args, **kwargs):
        if not request.user.is_admin():
            messages.error(request, 'No tienes permisos para acceder a esta página')
            return redirect('index')
        return function(request, *args, **kwargs)

    wrap.__doc__ = function.__doc__
    wrap.__name__ = function.__name__
    return wrap
