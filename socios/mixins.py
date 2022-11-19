from django.contrib.auth.mixins import AccessMixin


class SocioRequiredMixin(AccessMixin):
    """
    CBV mixin which verifies that the current user is socio.
    """
    permission_denied_message = 'No tiene permisos para acceder a esta página.'
    login_url = 'index'

    def dispatch(self, request, *args, **kwargs):
        try:
            if request.user.persona.get_socio() is None:
                return self.handle_no_permission()
        except AttributeError:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
