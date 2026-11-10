from django.db.models import OuterRef, Subquery
from rest_framework.response import Response
from rest_framework.views import APIView

from cuentas.permisos import EsLogistica
from tienda.models import ESTADO_DESPACHADO, Categoria, DetallePedido

from .models import Camion, Despacho, TelemetriaRuta


def despachos_activos():
    """Despacho activo = en ruta: sin fecha de entrega y con el pedido aun en estado Despachado."""
    return Despacho.objects.filter(fecha_entrega__isnull=True, pedido__estado__nombre=ESTADO_DESPACHADO)


def rangos_de_carga() -> dict:
    """
    Rango de conservacion por camion (regla de negocio "Alerta de frio"):
    con despacho activo, el mas estricto entre las categorias de los productos del pedido;
    sin despacho, el de Carnes congeladas. Devuelve {camion_id: (temp_min, temp_max)} + clave None = por defecto.
    """
    base = Categoria.objects.filter(nombre="Carnes congeladas").values_list("temp_min", "temp_max").first()
    rangos = {None: base or (-25, -18)}
    filas = (
        DetallePedido.objects.filter(pedido__despacho__in=despachos_activos())
        .values_list("pedido__despacho__camion_id", "producto__categoria__temp_min", "producto__categoria__temp_max")
        .distinct()
    )
    por_camion: dict[str, list] = {}
    for camion_id, t_min, t_max in filas:
        por_camion.setdefault(camion_id, []).append((t_min, t_max))
    for camion_id, lista in por_camion.items():
        t_min, t_max = max(r[0] for r in lista), min(r[1] for r in lista)
        if t_min >= t_max:
            # Carga mixta sin rango comun (congelado + refrigerado): manda la categoria mas fria.
            t_min, t_max = min(lista, key=lambda r: r[1])
        rangos[camion_id] = (t_min, t_max)
    return rangos


def _despacho_a_dict(d) -> dict:
    return {
        "id_despacho": d.id_despacho,
        "id_pedido": d.pedido_id,
        "camion_id": d.camion_id,
        "cliente": d.pedido.cliente.nombre_razon_social,
        "direccion_entrega": d.pedido.direccion_entrega,
        "estado_pedido": d.pedido.estado.nombre,
        "fecha_salida": d.fecha_salida,
        "fecha_entrega": d.fecha_entrega,
    }


class CamionesView(APIView):
    """GET /api/camiones?activo=1  (para elegir camion al despachar)"""

    permission_classes = [EsLogistica]

    def get(self, request):
        qs = Camion.objects.order_by("camion_id")
        if request.query_params.get("activo") in ("1", "true"):
            qs = qs.filter(activo=True)
        en_ruta: dict[str, int] = {}
        for camion_id in despachos_activos().values_list("camion_id", flat=True):
            en_ruta[camion_id] = en_ruta.get(camion_id, 0) + 1
        return Response(
            [
                {
                    "camion_id": c.camion_id,
                    "patente": c.patente,
                    "capacidad_kg": c.capacidad_kg,
                    "activo": c.activo,
                    "despachos_activos": en_ruta.get(c.camion_id, 0),
                }
                for c in qs
            ]
        )


class DespachosView(APIView):
    """GET /api/despachos?activos=1"""

    permission_classes = [EsLogistica]

    def get(self, request):
        qs = despachos_activos() if request.query_params.get("activos") in ("1", "true") else Despacho.objects.all()
        qs = qs.select_related("pedido__cliente", "pedido__estado").order_by("-fecha_salida")
        return Response([_despacho_a_dict(d) for d in qs])


class FlotaView(APIView):
    """GET /api/flota  -> ultima lectura IoT de cada camion y sus despachos en ruta."""

    permission_classes = [EsLogistica]

    def get(self, request):
        ultima = (
            TelemetriaRuta.objects.filter(camion=OuterRef("pk")).order_by("-fecha_hora").values("id_telemetria")[:1]
        )
        camiones = list(Camion.objects.annotate(id_ultima=Subquery(ultima)).order_by("camion_id"))
        lecturas = TelemetriaRuta.objects.in_bulk([c.id_ultima for c in camiones if c.id_ultima])
        en_ruta: dict[str, list] = {}
        for d in despachos_activos().select_related("pedido__cliente", "pedido__estado"):
            en_ruta.setdefault(d.camion_id, []).append(_despacho_a_dict(d))

        rangos = rangos_de_carga()
        salida = []
        for c in camiones:
            lectura = lecturas.get(c.id_ultima)
            t_min, t_max = rangos.get(c.camion_id, rangos[None])
            salida.append(
                {
                    "camion_id": c.camion_id,
                    "patente": c.patente,
                    "capacidad_kg": c.capacidad_kg,
                    "activo": c.activo,
                    "despachos": en_ruta.get(c.camion_id, []),
                    "rango": {"temp_min": t_min, "temp_max": t_max},
                    "lectura": {
                        "temp_camara": lectura.temp_camara,
                        "lat": lectura.lat,
                        "long": lectura.long,
                        "combustible_pct": lectura.combustible_pct,
                        "alerta_ruptura_frio": lectura.alerta_ruptura_frio,
                        "fecha_hora": lectura.fecha_hora,
                    }
                    if lectura
                    else None,
                }
            )
        return Response(salida)
