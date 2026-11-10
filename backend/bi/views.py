"""Dashboard BI: un solo JSON que cruza metricas comerciales con las alertas de cadena de frio IoT."""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, DecimalField, Exists, F, Max, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce, Now, TruncDate, TruncMinute
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.models import ETAPA_GANADO, ETAPA_PERDIDO, EtapaPipeline
from cuentas.permisos import EsAdministrador
from logistica.models import Camion, Despacho, TelemetriaRuta
from logistica.views import despachos_activos, rangos_de_carga
from tienda.models import ESTADO_DESPACHADO, ESTADO_RECHAZADO, ESTADOS, DetallePedido, Pedido

MONTO = Sum(F("cantidad") * F("precio_unitario"), output_field=DecimalField(max_digits=14, decimal_places=2))
# Una lectura cuenta como "ahora" si llego en los ultimos 2 minutos (si el simulador se cae, no hay alertas fantasma).
VIGENCIA_LECTURA = timedelta(minutes=2)


def _ventas(desde=None, **filtros) -> Decimal:
    qs = DetallePedido.objects.exclude(pedido__estado__nombre=ESTADO_RECHAZADO).filter(**filtros)
    if desde is not None:
        qs = qs.filter(pedido__fecha_creacion__gte=desde)
    return qs.aggregate(t=MONTO)["t"] or Decimal(0)


def _comercial(ahora):
    hoy = timezone.localdate()
    inicio_hoy = timezone.make_aware(timezone.datetime.combine(hoy, timezone.datetime.min.time()))
    inicio_7d = inicio_hoy - timedelta(days=6)
    pedidos_7d = Pedido.objects.filter(fecha_creacion__gte=inicio_7d)
    validos_7d = pedidos_7d.exclude(estado__nombre=ESTADO_RECHAZADO)

    # Ventas por dia y canal (ultimos 7 dias, incluido hoy)
    por_dia = {
        hoy - timedelta(days=d): {"fecha": hoy - timedelta(days=d), "web": 0, "vendedor": 0, "pedidos": 0}
        for d in range(6, -1, -1)
    }
    filas = (
        DetallePedido.objects.exclude(pedido__estado__nombre=ESTADO_RECHAZADO)
        .filter(pedido__fecha_creacion__gte=inicio_7d)
        .annotate(dia=TruncDate("pedido__fecha_creacion"))
        .values("dia", "pedido__canal")
        .annotate(monto=MONTO, pedidos=Count("pedido", distinct=True))
    )
    for f in filas:
        if f["dia"] in por_dia:
            por_dia[f["dia"]][f["pedido__canal"]] = f["monto"]
            por_dia[f["dia"]]["pedidos"] += f["pedidos"]

    def agrupar(campo, etiquetas=None):
        datos = {
            f[campo]: f
            for f in DetallePedido.objects.exclude(pedido__estado__nombre=ESTADO_RECHAZADO)
            .filter(pedido__fecha_creacion__gte=inicio_7d)
            .values(campo)
            .annotate(monto=MONTO, pedidos=Count("pedido", distinct=True))
        }
        claves = etiquetas or sorted(datos)
        return [
            {"nombre": k, "pedidos": datos.get(k, {}).get("pedidos", 0), "monto": datos.get(k, {}).get("monto", 0)}
            for k in claves
        ]

    por_canal = agrupar("pedido__canal", ["web", "vendedor"])
    total_pedidos = sum(c["pedidos"] for c in por_canal)
    estados = dict(pedidos_7d.values_list("estado__nombre").annotate(n=Count("pk")))

    etapas = list(
        EtapaPipeline.objects.order_by("orden").annotate(
            cantidad=Count("oportunidades"), monto=Coalesce(Sum("oportunidades__monto_estimado"), Decimal(0))
        )
    )
    total_op = sum(e.cantidad for e in etapas)
    ganadas = sum(e.cantidad for e in etapas if e.nombre == ETAPA_GANADO)
    perdidas = sum(e.cantidad for e in etapas if e.nombre == ETAPA_PERDIDO)

    return {
        "ventas_hoy": _ventas(inicio_hoy),
        "pedidos_hoy": Pedido.objects.filter(fecha_creacion__gte=inicio_hoy).exclude(estado__nombre=ESTADO_RECHAZADO).count(),
        "ventas_7d": _ventas(inicio_7d),
        "pedidos_7d": validos_7d.count(),
        "pct_pedidos_web": round(100 * por_canal[0]["pedidos"] / total_pedidos, 1) if total_pedidos else 0,
        "ventas_por_dia": list(por_dia.values()),
        "por_canal": por_canal,
        "por_perfil": agrupar("pedido__cliente__tipo__nombre", ["B2B", "B2C"]),
        "por_estado": [{"nombre": e, "pedidos": estados.get(e, 0)} for e in ESTADOS],
        "pipeline": {
            "etapas": [{"nombre": e.nombre, "oportunidades": e.cantidad, "monto": e.monto} for e in etapas],
            "oportunidades": total_op,
            "ganadas": ganadas,
            "perdidas": perdidas,
            "abiertas": total_op - ganadas - perdidas,
            # Conversion: oportunidades ganadas sobre el total que entro al pipeline
            "conversion_pct": round(100 * ganadas / total_op, 1) if total_op else 0,
        },
    }


def _lecturas_actuales(ahora):
    """Ultima lectura vigente de cada camion: {camion_id: TelemetriaRuta}."""
    ultima = TelemetriaRuta.objects.filter(camion=OuterRef("pk")).order_by("-fecha_hora").values("id_telemetria")[:1]
    ids = Camion.objects.annotate(id_ultima=Subquery(ultima)).values_list("id_ultima", flat=True)
    lecturas = TelemetriaRuta.objects.filter(pk__in=[i for i in ids if i], fecha_hora__gte=ahora - VIGENCIA_LECTURA)
    return {l.camion_id: l for l in lecturas}


def _operativo(ahora, actuales, rangos):
    hace_1h = ahora - timedelta(hours=1)
    ultima_hora = TelemetriaRuta.objects.filter(fecha_hora__gte=hace_1h)
    totales = ultima_hora.aggregate(
        lecturas=Count("pk"),
        alertas=Count("pk", filter=Q(alerta_ruptura_frio=True)),
        camiones_con_alerta=Count("camion", filter=Q(alerta_ruptura_frio=True), distinct=True),
        ultima=Max("fecha_hora"),
    )

    # Serie por minuto (ultimos 30 min): camiones distintos con al menos una lectura en alerta
    inicio = (ahora - timedelta(minutes=29)).replace(second=0, microsecond=0)
    por_minuto = dict(
        TelemetriaRuta.objects.filter(fecha_hora__gte=inicio, alerta_ruptura_frio=True)
        .annotate(minuto=TruncMinute("fecha_hora"))
        .values_list("minuto")
        .annotate(n=Count("camion", distinct=True))
    )
    serie = []
    for i in range(30):
        minuto = inicio + timedelta(minutes=i)
        serie.append({"minuto": minuto, "camiones_en_alerta": por_minuto.get(minuto, 0)})

    promedios = {
        f["camion_id"]: f
        for f in TelemetriaRuta.objects.filter(fecha_hora__gte=ahora - timedelta(minutes=15))
        .values("camion_id")
        .annotate(
            temp_promedio=Avg("temp_camara"),
            temp_maxima=Max("temp_camara"),
            alertas=Count("pk", filter=Q(alerta_ruptura_frio=True)),
        )
    }
    por_camion = []
    for camion_id in sorted(promedios):
        f = promedios[camion_id]
        t_min, t_max = rangos.get(camion_id, rangos[None])
        actual = actuales.get(camion_id)
        por_camion.append(
            {
                "camion_id": camion_id,
                "temp_promedio": round(f["temp_promedio"], 1),
                "temp_maxima": round(f["temp_maxima"], 1),
                "alertas_15min": f["alertas"],
                "temp_min_rango": t_min,
                "temp_max_rango": t_max,
                "en_alerta": bool(actual and actual.alerta_ruptura_frio),
            }
        )

    en_alerta = sorted(c for c, l in actuales.items() if l.alerta_ruptura_frio)
    return {
        "camiones_reportando": len(actuales),
        "camiones_en_alerta": len(en_alerta),
        "camiones_en_alerta_ids": en_alerta,
        "alertas_ultima_hora": totales["alertas"],
        "lecturas_ultima_hora": totales["lecturas"],
        "camiones_con_alerta_ultima_hora": totales["camiones_con_alerta"],
        "ultima_lectura": totales["ultima"],
        "alertas_por_minuto": serie,
        "temperatura_por_camion": por_camion,
    }


def _cruce(ahora, actuales, rangos):
    """Comercial x IoT: cuanta venta esta viajando ahora mismo en camiones con ruptura de frio."""
    activos = list(despachos_activos().select_related("pedido__cliente"))
    montos = dict(
        DetallePedido.objects.filter(pedido__in=[d.pedido_id for d in activos])
        .values_list("pedido_id")
        .annotate(m=MONTO)
    )
    en_riesgo = []
    for d in activos:
        lectura = actuales.get(d.camion_id)
        if lectura and lectura.alerta_ruptura_frio:
            t_min, t_max = rangos.get(d.camion_id, rangos[None])
            en_riesgo.append(
                {
                    "id_pedido": d.pedido_id,
                    "cliente": d.pedido.cliente.nombre_razon_social,
                    "canal": d.pedido.canal,
                    "camion_id": d.camion_id,
                    "temp_camara": lectura.temp_camara,
                    "temp_min_rango": t_min,
                    "temp_max_rango": t_max,
                    "monto": montos.get(d.pedido_id, 0),
                    "fecha_salida": d.fecha_salida,
                }
            )
    en_riesgo.sort(key=lambda p: p["monto"], reverse=True)
    monto_en_ruta = sum(montos.values(), Decimal(0))
    monto_en_riesgo = sum((p["monto"] for p in en_riesgo), Decimal(0))

    # % de despachos (historicos y en ruta) que tuvieron al menos una alerta mientras viajaban
    alerta_en_viaje = TelemetriaRuta.objects.filter(
        camion_id=OuterRef("camion_id"),
        alerta_ruptura_frio=True,
        fecha_hora__gte=OuterRef("fecha_salida"),
        fecha_hora__lte=Coalesce(OuterRef("fecha_entrega"), Now()),
    )
    despachos = Despacho.objects.exclude(
        Q(fecha_entrega__isnull=True) & ~Q(pedido__estado__nombre=ESTADO_DESPACHADO)
    ).annotate(con_alerta=Exists(alerta_en_viaje))
    total = despachos.count()
    con_alerta = despachos.filter(con_alerta=True).count()
    activos_con_alerta = despachos.filter(con_alerta=True, fecha_entrega__isnull=True).count()

    return {
        "pedidos_en_ruta": len(activos),
        "monto_en_ruta": monto_en_ruta,
        "pedidos_en_riesgo": en_riesgo,
        "monto_en_riesgo": monto_en_riesgo,
        "pct_monto_en_riesgo": round(100 * float(monto_en_riesgo) / float(monto_en_ruta), 1) if monto_en_ruta else 0,
        "despachos_total": total,
        "despachos_con_alerta": con_alerta,
        "pct_despachos_con_alerta": round(100 * con_alerta / total, 1) if total else 0,
        "despachos_en_ruta_con_alerta": activos_con_alerta,
    }


class ResumenView(APIView):
    """GET /api/bi/resumen  (solo administrador)"""

    permission_classes = [EsAdministrador]

    def get(self, request):
        ahora = timezone.now()
        actuales = _lecturas_actuales(ahora)
        rangos = rangos_de_carga()
        return Response(
            {
                "generado": ahora,
                "comercial": _comercial(ahora),
                "operativo": _operativo(ahora, actuales, rangos),
                "cruce": _cruce(ahora, actuales, rangos),
            }
        )
