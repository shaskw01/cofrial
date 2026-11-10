"""Permisos por rol (CLAUDE.md, "Reglas de negocio clave" -> Roles)."""

from rest_framework.permissions import BasePermission

from .models import ROL_ADMINISTRADOR, ROL_CLIENTE, ROL_DESPACHADOR, ROL_VENDEDOR


def rol_de(usuario) -> str | None:
    if not usuario or not usuario.is_authenticated:
        return None
    return usuario.rol.nombre


class TieneRol(BasePermission):
    """Permite el acceso solo a usuarios activos cuyo rol este en `roles`."""

    roles: tuple[str, ...] = ()
    message = "Tu rol no tiene permiso para esta acción."

    def has_permission(self, request, view):
        return rol_de(request.user) in self.roles


def roles(*nombres: str) -> type[TieneRol]:
    return type("TieneRol_" + "_".join(nombres), (TieneRol,), {"roles": nombres})


EsAdministrador = roles(ROL_ADMINISTRADOR)
EsCliente = roles(ROL_CLIENTE)
# CRM: vendedor y administrador
EsCRM = roles(ROL_ADMINISTRADOR, ROL_VENDEDOR)
# Pedidos, despachos y flota: despachador y administrador
EsLogistica = roles(ROL_ADMINISTRADOR, ROL_DESPACHADOR)
# Cualquier usuario interno (panel)
EsInterno = roles(ROL_ADMINISTRADOR, ROL_VENDEDOR, ROL_DESPACHADOR)
