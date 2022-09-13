from django.contrib.auth.decorators import user_passes_test


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
