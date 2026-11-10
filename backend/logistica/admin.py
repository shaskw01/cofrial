from django.contrib import admin

from .models import Camion, Despacho, TelemetriaRuta


@admin.register(Camion)
class CamionAdmin(admin.ModelAdmin):
    list_display = ("camion_id", "patente", "capacidad_kg", "activo")
    list_filter = ("activo",)
    search_fields = ("camion_id", "patente")


@admin.register(Despacho)
class DespachoAdmin(admin.ModelAdmin):
    list_display = ("id_despacho", "pedido", "camion", "fecha_salida", "fecha_entrega")
    list_filter = ("camion",)


@admin.register(TelemetriaRuta)
class TelemetriaRutaAdmin(admin.ModelAdmin):
    list_display = ("fecha_hora", "camion", "temp_camara", "lat", "long", "combustible_pct", "alerta_ruptura_frio")
    list_filter = ("alerta_ruptura_frio", "camion")
    readonly_fields = ("fecha_hora",)
