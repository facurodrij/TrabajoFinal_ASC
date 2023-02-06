from django.contrib.auth.mixins import AccessMixin


class AdminRequiredMixin(AccessMixin):
    """
    CBV mixin, which verifies that the current user is admin.
    """
    permission_denied_message = 'Para acceder a esta página debe ser un administrador.'

    def dispatch(self, request, *args, **kwargs):
        try:
            if not request.user.is_admin():
                return self.handle_no_permission()
        except AttributeError:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
