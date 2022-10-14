from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Persona
from .forms import CustomUserCreationForm, CustomUserChangeForm


class CustomUserAdmin(UserAdmin):
    """
    Formulario para registrar un nuevo usuario. Excluir los campos first_name y last_name.
    """
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ["email"]}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2"),
            },
        ),
    )
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    list_display = ("username", "email", "is_staff")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "email")


class PersonaAdmin(admin.ModelAdmin):
    """
    Formulario para registrar una nueva persona.
    """
    fieldsets = (
        (None, {"fields": ("dni", "nombre", "apellido")}),
        (_("Información adicional"), {"fields": ["sexo", "fecha_nacimiento", "direccion", "localidad"]}),
    )
    list_display = ("dni", "nombre", "apellido")
    search_fields = ("dni", "nombre", "apellido")


admin.site.register(User, CustomUserAdmin)
admin.site.register(Persona, PersonaAdmin)
