from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.models import Cliente
from cuentas.models import ROL_CLIENTE
from cuentas.permisos import EsCliente, EsInterno, EsLogistica, rol_de

from .models import ESTADOS, TIPO_B2B, TIPO_B2C, Categoria, ListaPrecio, Pedido, Producto
from .servicios import StockInsuficiente, TransicionInvalida, cambiar_estado, crear_pedido


# ---------------------------------------------------------------- catalogo
def tipo_precio_para(request) -> str:
    """Perfil de precios: el del cliente logueado; visitante = B2C; interno puede pedir ?tipo=B2B."""
    rol = rol_de(request.user)
    if rol == ROL_CLIENTE:
        cliente = Cliente.objects.select_related("tipo").filter(usuario=request.user).first()
        return cliente.tipo.nombre if cliente else TIPO_B2C
    if rol and request.query_params.get("tipo") == TIPO_B2B:
        return TIPO_B2B
    return TIPO_B2C


class CategoriasView(APIView):
    """GET /api/categorias"""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            [
                {
                    "id_categoria": c.id_categoria,
                    "nombre": c.nombre,
                    "temp_min": c.temp_min,
                    "temp_max": c.temp_max,
                }
                for c in Categoria.objects.order_by("nombre")
            ]
        )


class ProductosView(APIView):
    """GET /api/productos?categoria=<id|nombre>&q=<texto>  (precio segun perfil)"""

    permission_classes = [AllowAny]

    def get(self, request):
        tipo = tipo_precio_para(request)
        qs = Producto.objects.select_related("categoria").order_by("categoria__nombre", "nombre")
        categoria = request.query_params.get("categoria")
        if categoria:
            qs = qs.filter(categoria_id=categoria) if categoria.isdigit() else qs.filter(
                categoria__nombre__iexact=categoria
            )
        texto = request.query_params.get("q")
        if texto:
            qs = qs.filter(Q(nombre__icontains=texto) | Q(sku__icontains=texto))

        precios = dict(ListaPrecio.objects.filter(tipo__nombre=tipo).values_list("producto_id", "precio"))
        return Response(
            [
                {
                    "id_producto": p.id_producto,
                    "sku": p.sku,
                    "nombre": p.nombre,
                    "unidad_medida": p.unidad_medida,
                    "stock_disponible": p.stock_disponible,
                    "precio": precios.get(p.id_producto),
                    "tipo_precio": tipo,
                    "categoria": {
                        "id_categoria": p.categoria.id_categoria,
                        "nombre": p.categoria.nombre,
                        "temp_min": p.categoria.temp_min,
                        "temp_max": p.categoria.temp_max,
                    },
                }
                for p in qs
            ]
        )


# ---------------------------------------------------------------- pedidos
def _pedidos_qs():
    return Pedido.objects.select_related("cliente__tipo", "estado", "despacho").prefetch_related(
        "detalles__producto"
    )


def pedido_a_dict(pedido) -> dict:
    detalles = [
        {
            "id_producto": d.producto_id,
            "sku": d.producto.sku,
            "nombre": d.producto.nombre,
            "unidad_medida": d.producto.unidad_medida,
            "cantidad": d.cantidad,
            "precio_unitario": d.precio_unitario,
            "subtotal": d.subtotal,
        }
        for d in pedido.detalles.all()
    ]
    despacho = getattr(pedido, "despacho", None)
    return {
        "id_pedido": pedido.id_pedido,
        "cliente": {
            "id_cliente": pedido.cliente_id,
            "nombre_razon_social": pedido.cliente.nombre_razon_social,
            "tipo": pedido.cliente.tipo.nombre,
        },
        "estado": pedido.estado.nombre,
        "canal": pedido.canal,
        "numero_oc": pedido.numero_oc,
        "fecha_entrega_solicitada": pedido.fecha_entrega_solicitada,
        "direccion_entrega": pedido.direccion_entrega,
        "fecha_creacion": pedido.fecha_creacion,
        "total": sum(d["subtotal"] for d in detalles),
        "detalles": detalles,
        "despacho": {
            "id_despacho": despacho.id_despacho,
            "camion_id": despacho.camion_id,
            "fecha_salida": despacho.fecha_salida,
            "fecha_entrega": despacho.fecha_entrega,
        }
        if despacho
        else None,
    }


class ItemSerializer(serializers.Serializer):
    id_producto = serializers.IntegerField(min_value=1)
    cantidad = serializers.IntegerField(min_value=1)


class CheckoutSerializer(serializers.Serializer):
    items = ItemSerializer(many=True, allow_empty=False)
    fecha_entrega_solicitada = serializers.DateField()
    direccion_entrega = serializers.CharField(max_length=200, required=False, allow_blank=True)
    numero_oc = serializers.CharField(max_length=30, required=False, allow_blank=True, allow_null=True)
    # Solo para pedidos ingresados por un vendedor a nombre de un cliente (canal "vendedor")
    id_cliente = serializers.IntegerField(required=False)

    def validate_fecha_entrega_solicitada(self, fecha):
        if fecha < timezone.localdate():
            raise serializers.ValidationError("La fecha de entrega no puede ser anterior a hoy.")
        return fecha


class PedidosView(APIView):
    """
    GET  /api/pedidos?estado=&canal=&cliente=   listado interno (administrador, vendedor, despachador)
    POST /api/pedidos                            checkout (cliente -> canal web; vendedor con id_cliente -> canal vendedor)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not EsInterno().has_permission(request, self):
            raise PermissionDenied("Los clientes consultan sus pedidos en /api/mis-pedidos.")
        qs = _pedidos_qs().order_by("-fecha_creacion")
        estado = request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado__nombre__iexact=estado)
        canal = request.query_params.get("canal")
        if canal:
            qs = qs.filter(canal=canal)
        cliente = request.query_params.get("cliente")
        if cliente:
            qs = qs.filter(cliente_id=cliente)
        return Response([pedido_a_dict(p) for p in qs])

    def post(self, request):
        datos = CheckoutSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        v = datos.validated_data

        rol = rol_de(request.user)
        if rol == ROL_CLIENTE:
            cliente = Cliente.objects.select_related("tipo").filter(usuario=request.user).first()
            if cliente is None:
                raise PermissionDenied("Tu cuenta no tiene un perfil de cliente asociado.")
            canal = Pedido.CANAL_WEB
        elif rol in ("vendedor", "administrador"):
            if not v.get("id_cliente"):
                raise serializers.ValidationError({"id_cliente": "Indica el cliente para quien se ingresa el pedido."})
            cliente = get_object_or_404(Cliente.objects.select_related("tipo"), pk=v["id_cliente"])
            canal = Pedido.CANAL_VENDEDOR
        else:
            raise PermissionDenied("Tu rol no puede crear pedidos.")

        try:
            pedido = crear_pedido(
                cliente=cliente,
                items=v["items"],
                fecha_entrega_solicitada=v["fecha_entrega_solicitada"],
                direccion_entrega=v.get("direccion_entrega"),
                numero_oc=v.get("numero_oc"),
                canal=canal,
            )
        except StockInsuficiente as e:
            return Response(
                {"detail": "Stock insuficiente para completar el pedido.", "faltantes": e.faltantes},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(pedido_a_dict(_pedidos_qs().get(pk=pedido.pk)), status=status.HTTP_201_CREATED)


class MisPedidosView(APIView):
    """GET /api/mis-pedidos  (pedidos del cliente logueado)"""

    permission_classes = [EsCliente]

    def get(self, request):
        qs = _pedidos_qs().filter(cliente__usuario=request.user).order_by("-fecha_creacion")
        return Response([pedido_a_dict(p) for p in qs])


class EstadoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=ESTADOS)
    camion_id = serializers.CharField(max_length=10, required=False, allow_blank=True)


class PedidoDetalleView(APIView):
    """
    GET   /api/pedidos/{id}                          interno, o el cliente dueño del pedido
    PATCH /api/pedidos/{id}  {estado, camion_id?}    despachador o administrador
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, id_pedido):
        pedido = get_object_or_404(_pedidos_qs(), pk=id_pedido)
        if rol_de(request.user) == ROL_CLIENTE and pedido.cliente.usuario_id != request.user.pk:
            raise PermissionDenied("Este pedido no es tuyo.")
        return Response(pedido_a_dict(pedido))

    def patch(self, request, id_pedido):
        if not EsLogistica().has_permission(request, self):
            raise PermissionDenied("Solo despacho o administración pueden cambiar el estado de un pedido.")
        get_object_or_404(Pedido, pk=id_pedido)
        datos = EstadoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        try:
            cambiar_estado(
                id_pedido=id_pedido,
                nuevo_estado=datos.validated_data["estado"],
                camion_id=datos.validated_data.get("camion_id"),
            )
        except TransicionInvalida as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(pedido_a_dict(_pedidos_qs().get(pk=id_pedido)))
