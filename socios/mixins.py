from django.contrib.auth.mixins import AccessMixin


class SocioRequiredMixin(AccessMixin):
    """
    CBV mixin, which verifies that the current user is socio.
    """
    permission_denied_message = 'Para acceder a esta página debe ser un socio activo.'

    def dispatch(self, request, *args, **kwargs):
        try:
            if not request.user.get_socio():
                return self.handle_no_permission()
        except AttributeError:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
