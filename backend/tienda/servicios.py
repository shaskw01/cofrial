"""Reglas de negocio de la tienda: precios por perfil, checkout atomico y estados del pedido."""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from logistica.models import Camion, Despacho

from .models import (
    ESTADO_DESPACHADO,
    ESTADO_EN_PREPARACION,
    ESTADO_ENTREGADO,
    ESTADO_RECHAZADO,
    ESTADO_RECIBIDO,
    TIPO_B2B,
    DetallePedido,
    EstadoPedido,
    ListaPrecio,
    Pedido,
    Producto,
)

# Recibido -> En preparación -> Despachado -> Entregado | Rechazado
TRANSICIONES = {
    ESTADO_RECIBIDO: {ESTADO_EN_PREPARACION, ESTADO_RECHAZADO},
    ESTADO_EN_PREPARACION: {ESTADO_DESPACHADO, ESTADO_RECHAZADO},
    ESTADO_DESPACHADO: {ESTADO_ENTREGADO, ESTADO_RECHAZADO},
    ESTADO_ENTREGADO: set(),
    ESTADO_RECHAZADO: set(),
}


class StockInsuficiente(Exception):
    def __init__(self, faltantes):
        super().__init__("Stock insuficiente")
        self.faltantes = faltantes


class TransicionInvalida(Exception):
    pass


@transaction.atomic
def crear_pedido(*, cliente, items, fecha_entrega_solicitada, direccion_entrega=None, numero_oc=None, canal="web"):
    """
    Checkout atomico: bloquea los productos, valida stock, descuenta y crea pedido + detalle.

    `items` es una lista de dicts {id_producto, cantidad}. Lanza StockInsuficiente (-> 409).
    """
    es_b2b = cliente.tipo.nombre == TIPO_B2B
    numero_oc = (numero_oc or "").strip() or None
    if es_b2b and not numero_oc:
        raise ValidationError({"numero_oc": "Los clientes B2B deben ingresar el N.º de orden de compra."})
    if not es_b2b:
        numero_oc = None

    cantidades: dict[int, int] = {}
    for item in items:
        cantidades[item["id_producto"]] = cantidades.get(item["id_producto"], 0) + item["cantidad"]

    # Orden fijo por PK para que dos checkouts simultaneos no se bloqueen entre si.
    productos = {
        p.pk: p for p in Producto.objects.select_for_update().filter(pk__in=cantidades).order_by("pk")
    }
    inexistentes = sorted(set(cantidades) - set(productos))
    if inexistentes:
        raise ValidationError({"items": f"Productos inexistentes: {inexistentes}"})

    precios = dict(
        ListaPrecio.objects.filter(tipo=cliente.tipo, producto_id__in=list(cantidades)).values_list(
            "producto_id", "precio"
        )
    )
    sin_precio = [productos[pk].sku for pk in cantidades if pk not in precios]
    if sin_precio:
        raise ValidationError({"items": f"Productos sin precio para el perfil {cliente.tipo.nombre}: {sin_precio}"})

    faltantes = [
        {
            "id_producto": pk,
            "sku": productos[pk].sku,
            "nombre": productos[pk].nombre,
            "solicitado": cantidad,
            "disponible": productos[pk].stock_disponible,
        }
        for pk, cantidad in cantidades.items()
        if cantidad > productos[pk].stock_disponible
    ]
    if faltantes:
        raise StockInsuficiente(faltantes)

    pedido = Pedido.objects.create(
        cliente=cliente,
        estado=EstadoPedido.objects.get(nombre=ESTADO_RECIBIDO),
        canal=canal,
        numero_oc=numero_oc,
        fecha_entrega_solicitada=fecha_entrega_solicitada,
        direccion_entrega=(direccion_entrega or "").strip() or cliente.direccion_despacho,
    )
    detalles = []
    for pk, cantidad in cantidades.items():
        producto = productos[pk]
        producto.stock_disponible -= cantidad
        producto.save(update_fields=["stock_disponible"])
        detalles.append(
            DetallePedido(pedido=pedido, producto=producto, cantidad=cantidad, precio_unitario=precios[pk])
        )
    DetallePedido.objects.bulk_create(detalles)
    return pedido


@transaction.atomic
def cambiar_estado(*, id_pedido, nuevo_estado, camion_id=None):
    """
    Aplica una transicion de estado. Despachado exige camion (crea el despacho);
    Entregado completa despachos.fecha_entrega.
    """
    pedido = Pedido.objects.select_for_update(of=("self",)).select_related("estado").get(pk=id_pedido)
    actual = pedido.estado.nombre
    if nuevo_estado not in TRANSICIONES.get(actual, set()):
        permitidos = ", ".join(sorted(TRANSICIONES.get(actual, set()))) or "ninguno (estado final)"
        raise TransicionInvalida(
            f"No se puede pasar de «{actual}» a «{nuevo_estado}». Estados permitidos: {permitidos}."
        )

    ahora = timezone.now()
    if nuevo_estado == ESTADO_DESPACHADO:
        if not camion_id:
            raise ValidationError({"camion_id": "Para despachar hay que elegir un camión."})
        camion = Camion.objects.filter(pk=camion_id).first()
        if camion is None:
            raise ValidationError({"camion_id": f"El camión {camion_id} no existe."})
        if not camion.activo:
            raise ValidationError({"camion_id": f"El camión {camion_id} no está operativo."})
        Despacho.objects.create(pedido=pedido, camion=camion, fecha_salida=ahora)
    elif nuevo_estado == ESTADO_ENTREGADO:
        Despacho.objects.filter(pedido=pedido).update(fecha_entrega=ahora)

    pedido.estado = EstadoPedido.objects.get(nombre=nuevo_estado)
    pedido.save(update_fields=["estado"])
    return pedido
