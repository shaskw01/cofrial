"""Reglas de negocio del CRM: alta de clientes y pipeline comercial."""

import os

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from cuentas.models import ROL_CLIENTE, Usuario
from tienda.models import TIPO_B2B, TipoCliente

from .models import ETAPA_GANADO, ETAPA_PERDIDO, Cliente, Oportunidad, Prospecto


def password_inicial() -> str:
    """Las cuentas creadas desde el CRM parten con la contraseña demo (.env), nunca una escrita en el codigo."""
    password = os.environ.get("DEMO_PASSWORD")
    if not password:
        raise ValidationError({"detail": "Falta DEMO_PASSWORD en el entorno para crear la cuenta del cliente."})
    return password


def crear_usuario_cliente(email: str, password: str | None = None) -> Usuario:
    email = email.strip().lower()
    if Usuario.objects.filter(email__iexact=email).exists():
        raise ValidationError({"email": "Ya existe una cuenta con este correo."})
    return Usuario.objects.create_user(email, password or password_inicial(), rol=ROL_CLIENTE)


def _convertir_en_cliente(prospecto: Prospecto, *, direccion_despacho, telefono, rut) -> Cliente:
    """Pipeline -> Ganado: crea el cliente B2B y su usuario, y guarda prospectos.id_cliente."""
    usuario = Usuario.objects.filter(email__iexact=prospecto.email).first()
    cliente = Cliente.objects.filter(usuario=usuario).first() if usuario else None

    if cliente is None:
        rut = (rut or prospecto.rut or "").strip()
        telefono = (telefono or prospecto.telefono or "").strip()
        direccion_despacho = (direccion_despacho or "").strip()
        errores = {}
        if not rut:
            errores["rut"] = "El RUT es obligatorio para crear un cliente B2B."
        elif Cliente.objects.filter(rut=rut).exists():
            errores["rut"] = "Ya existe un cliente con este RUT."
        if not telefono:
            errores["telefono"] = "Indica un teléfono de contacto para el cliente."
        if not direccion_despacho:
            errores["direccion_despacho"] = "Indica la dirección de despacho del nuevo cliente."
        if usuario is not None and usuario.rol.nombre != ROL_CLIENTE:
            errores["email"] = "El correo del prospecto pertenece a una cuenta interna de Cofrial."
        if errores:
            raise ValidationError(errores)

        if usuario is None:
            usuario = crear_usuario_cliente(prospecto.email)
        cliente = Cliente.objects.create(
            usuario=usuario,
            tipo=TipoCliente.objects.get(nombre=TIPO_B2B),
            vendedor=prospecto.vendedor,
            nombre_razon_social=prospecto.razon_social,
            rut=rut,
            telefono=telefono,
            direccion_despacho=direccion_despacho,
        )
        if not prospecto.rut:
            prospecto.rut = rut
    elif Prospecto.objects.filter(cliente=cliente).exclude(pk=prospecto.pk).exists():
        raise ValidationError({"email": "El cliente de este correo ya está asociado a otro prospecto."})

    prospecto.cliente = cliente
    prospecto.save(update_fields=["cliente", "rut"])
    return cliente


@transaction.atomic
def actualizar_oportunidad(
    oportunidad: Oportunidad, *, etapa=None, monto_estimado=None, direccion_despacho=None, telefono=None, rut=None
) -> Oportunidad:
    oportunidad = (
        Oportunidad.objects.select_for_update(of=("self",))
        .select_related("etapa", "prospecto__vendedor")
        .get(pk=oportunidad.pk)
    )
    if monto_estimado is not None:
        oportunidad.monto_estimado = monto_estimado

    if etapa is not None and etapa.pk != oportunidad.etapa_id:
        if etapa.nombre == ETAPA_GANADO:
            prospecto = Prospecto.objects.select_for_update(of=("self",)).get(pk=oportunidad.prospecto_id)
            if prospecto.cliente_id is None:
                _convertir_en_cliente(
                    prospecto, direccion_despacho=direccion_despacho, telefono=telefono, rut=rut
                )
                prospecto.vendedor = oportunidad.prospecto.vendedor
                oportunidad.prospecto = prospecto  # la respuesta debe mostrar el id_cliente recien creado
        cerrada = etapa.nombre in (ETAPA_GANADO, ETAPA_PERDIDO)
        oportunidad.fecha_cierre = timezone.now() if cerrada else None
        oportunidad.etapa = etapa

    oportunidad.save()
    return oportunidad
