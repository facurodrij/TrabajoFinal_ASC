from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _

from accounts.models import User


class CustomUserAdmin(UserAdmin):
    """
    Formulario para registrar un nuevo usuario desde el panel de administrador.
    Excluir los campos 'first_name' y 'last_name'.
    """
    fieldsets = (
        ("Usuario info", {"fields": ("nombre", "apellido", "email", "password")}),
        (_("Permissions"),
         {
             "fields": (
                 "is_active",
                 "is_staff",
                 "is_superuser",
                 "groups",
                 "user_permissions",
             ),
         }),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "fields": ("nombre", "apellido", "email", "password1", "password2",
                           "is_staff", "is_superuser", "is_active", "notificaciones"),
            },
        ),
    )
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = ("email", "is_staff", "notificaciones")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ["email"]
    ordering = ["email"]


admin.site.register(User, CustomUserAdmin)
