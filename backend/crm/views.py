from django.db import transaction
from django.db.models import Count, ProtectedError
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from cuentas.models import ROL_VENDEDOR
from cuentas.permisos import EsCRM, EsInterno, rol_de

from .models import Cliente, EtapaPipeline, Interaccion, Oportunidad, Prospecto, Vendedor
from .serializers import (
    ClienteSerializer,
    EtapaSerializer,
    InteraccionSerializer,
    OportunidadSerializer,
    ProspectoSerializer,
    VendedorSerializer,
)

METODOS = ["get", "post", "patch", "delete", "head", "options"]


def _vendedor_de(request):
    """Vendedor al que se limita la vista; None = sin limite (administrador)."""
    if rol_de(request.user) != ROL_VENDEDOR:
        return None
    return Vendedor.objects.filter(usuario=request.user).first() or Vendedor(pk=0)


class VendedorViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/vendedores"""

    permission_classes = [EsCRM]
    queryset = Vendedor.objects.select_related("usuario").order_by("nombre")
    serializer_class = VendedorSerializer


class EtapaViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/etapas  (columnas del Kanban)"""

    permission_classes = [EsCRM]
    queryset = EtapaPipeline.objects.order_by("orden")
    serializer_class = EtapaSerializer


class ClienteViewSet(viewsets.ModelViewSet):
    """CRUD /api/clientes?tipo=B2B|B2C&q=  (lectura tambien para despacho)"""

    serializer_class = ClienteSerializer
    http_method_names = METODOS

    def get_permissions(self):
        return [EsInterno()] if self.action in ("list", "retrieve") else [EsCRM()]

    def get_queryset(self):
        qs = (
            Cliente.objects.select_related("usuario", "tipo", "vendedor")
            .annotate(total_pedidos=Count("pedidos"))
            .order_by("nombre_razon_social")
        )
        tipo = self.request.query_params.get("tipo")
        if tipo:
            qs = qs.filter(tipo__nombre__iexact=tipo)
        texto = self.request.query_params.get("q")
        if texto:
            qs = qs.filter(nombre_razon_social__icontains=texto)
        return qs

    def destroy(self, request, *args, **kwargs):
        cliente = self.get_object()
        usuario = cliente.usuario
        try:
            with transaction.atomic():
                cliente.delete()
                usuario.delete()
        except ProtectedError:
            return Response(
                {"detail": "No se puede eliminar: el cliente tiene pedidos registrados."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProspectoViewSet(viewsets.ModelViewSet):
    """CRUD /api/prospectos  (el vendedor ve solo los suyos)"""

    permission_classes = [EsCRM]
    serializer_class = ProspectoSerializer
    http_method_names = METODOS

    def get_queryset(self):
        qs = (
            Prospecto.objects.select_related("vendedor")
            .prefetch_related("oportunidades__etapa")
            .order_by("razon_social")
        )
        vendedor = _vendedor_de(self.request)
        return qs.filter(vendedor=vendedor) if vendedor else qs


class OportunidadViewSet(viewsets.ModelViewSet):
    """
    /api/oportunidades?etapa=
    PATCH {etapa: "Ganado", direccion_despacho, telefono?, rut?} crea el cliente B2B y su usuario.
    """

    permission_classes = [EsCRM]
    serializer_class = OportunidadSerializer
    http_method_names = METODOS

    def get_queryset(self):
        qs = Oportunidad.objects.select_related("etapa", "prospecto__vendedor").order_by("etapa__orden", "-fecha_creacion")
        vendedor = _vendedor_de(self.request)
        if vendedor:
            qs = qs.filter(prospecto__vendedor=vendedor)
        etapa = self.request.query_params.get("etapa")
        if etapa:
            qs = qs.filter(etapa__nombre__iexact=etapa)
        return qs


class InteraccionViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """GET /api/interacciones?oportunidad=&cliente=   POST /api/interacciones"""

    permission_classes = [EsCRM]
    serializer_class = InteraccionSerializer

    def get_queryset(self):
        qs = Interaccion.objects.order_by("-fecha")
        oportunidad = self.request.query_params.get("oportunidad")
        if oportunidad:
            qs = qs.filter(oportunidad_id=oportunidad)
        cliente = self.request.query_params.get("cliente")
        if cliente:
            qs = qs.filter(cliente_id=cliente)
        return qs
