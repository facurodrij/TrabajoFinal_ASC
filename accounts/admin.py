from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Persona
from .forms import *


class CustomUserAdmin(UserAdmin):
    """
    Formulario para registrar un nuevo usuario desde el panel de administrador.
    Excluir los campos 'first_name' y 'last_name'.
    """
    fieldsets = (
        ("Usuario info", {"fields": ("username", "email", "password")}),
        (_("Personal info"), {"fields": ["persona"]}),
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
                "fields": ("persona", "username", "email", "password1", "password2"),
            },
        ),
    )
    form = UpdateUserFormAdmin
    add_form = CreateUserFormAdmin
    list_display = ("username", "email", "is_staff")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "email")


class PersonaAdmin(admin.ModelAdmin):
    """
    Formulario para registrar una nueva persona desde el panel de administrador.
    """
    fieldsets = (
        ("Información personal", {"fields": ("dni", "nombre", "apellido", "sexo", "fecha_nacimiento")}),
        (_("Información adicional"), {"fields": ["club"]}),
    )
    list_display = ("dni", "nombre", "apellido")
    search_fields = ("dni", "nombre", "apellido")


admin.site.register(User, CustomUserAdmin)
admin.site.register(Persona, PersonaAdmin)
