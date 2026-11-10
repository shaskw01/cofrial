from django.contrib import admin

from .models import Cliente, EtapaPipeline, Interaccion, Oportunidad, Prospecto, Vendedor


@admin.register(Vendedor)
class VendedorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "usuario", "telefono")


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre_razon_social", "tipo", "rut", "vendedor", "telefono")
    list_filter = ("tipo", "vendedor")
    search_fields = ("nombre_razon_social", "rut", "usuario__email")


@admin.register(Prospecto)
class ProspectoAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "contacto", "email", "vendedor", "cliente")
    search_fields = ("razon_social", "contacto", "email")


@admin.register(EtapaPipeline)
class EtapaPipelineAdmin(admin.ModelAdmin):
    list_display = ("orden", "nombre")


@admin.register(Oportunidad)
class OportunidadAdmin(admin.ModelAdmin):
    list_display = ("id_oportunidad", "prospecto", "etapa", "monto_estimado", "fecha_creacion", "fecha_cierre")
    list_filter = ("etapa",)
    readonly_fields = ("fecha_creacion",)


@admin.register(Interaccion)
class InteraccionAdmin(admin.ModelAdmin):
    list_display = ("fecha", "tipo", "oportunidad", "cliente")
    list_filter = ("tipo",)
    readonly_fields = ("fecha",)
