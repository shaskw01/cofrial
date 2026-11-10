from django import forms
from django.contrib import admin

from .models import Rol, Usuario


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("id_rol", "nombre")


class UsuarioForm(forms.ModelForm):
    nueva_password = forms.CharField(
        label="Nueva contraseña",
        required=False,
        widget=forms.PasswordInput,
        help_text="Déjala vacía para mantener la actual.",
    )

    class Meta:
        model = Usuario
        fields = ("email", "rol", "activo")

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get("nueva_password"):
            usuario.set_password(self.cleaned_data["nueva_password"])
        elif not usuario.pk:
            usuario.set_unusable_password()
        if commit:
            usuario.save()
        return usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    form = UsuarioForm
    list_display = ("email", "rol", "activo", "fecha_creacion")
    list_filter = ("rol", "activo")
    search_fields = ("email",)
    readonly_fields = ("fecha_creacion",)
