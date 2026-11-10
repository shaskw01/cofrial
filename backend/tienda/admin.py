from django.contrib import admin
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.utils.html import format_html, format_html_join

from .models import TIPO_B2B, TIPO_B2C, Categoria, DetallePedido, EstadoPedido, Pedido, Producto, TipoCliente


def _clp(valor):
    return "—" if valor is None else f"${valor:,.0f}".replace(",", ".")


@admin.register(TipoCliente)
class TipoClienteAdmin(admin.ModelAdmin):
    list_display = ("id_tipo", "nombre")


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "temp_min", "temp_max")


@admin.register(EstadoPedido)
class EstadoPedidoAdmin(admin.ModelAdmin):
    list_display = ("id_estado", "nombre")


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("sku", "nombre", "categoria", "unidad_medida", "stock_disponible", "precio_b2b", "precio_b2c")
    list_filter = ("categoria",)
    search_fields = ("sku", "nombre")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("categoria").prefetch_related("precios__tipo")

    def _precio(self, obj, tipo):
        return _clp(next((p.precio for p in obj.precios.all() if p.tipo.nombre == tipo), None))

    @admin.display(description="Precio B2B")
    def precio_b2b(self, obj):
        return self._precio(obj, TIPO_B2B)

    @admin.display(description="Precio B2C")
    def precio_b2c(self, obj):
        return self._precio(obj, TIPO_B2C)


# Nota: ListaPrecio y DetallePedido tienen PK compuesta (como exige el modelo 3FN) y el admin de
# Django 5.2 no permite registrarlos. Se muestran dentro de Producto (columnas de precio) y Pedido (lineas).


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id_pedido", "cliente", "estado", "canal", "numero_oc", "fecha_creacion", "total")
    list_filter = ("estado", "canal", "cliente__tipo")
    search_fields = ("cliente__nombre_razon_social", "numero_oc")
    readonly_fields = ("fecha_creacion", "lineas")
    date_hierarchy = "fecha_creacion"

    @admin.display(description="Líneas del pedido")
    def lineas(self, obj):
        filas = [
            (d.producto.sku, d.producto.nombre, d.cantidad, _clp(d.precio_unitario), _clp(d.subtotal))
            for d in DetallePedido.objects.filter(pedido=obj).select_related("producto")
        ]
        if not filas:
            return "—"
        return format_html(
            "<table><tr><th>SKU</th><th>Producto</th><th>Cant.</th><th>P. unitario</th><th>Subtotal</th></tr>{}</table>",
            format_html_join("", "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>", filas),
        )

    def get_queryset(self, request):
        subtotal = ExpressionWrapper(
            F("detalles__cantidad") * F("detalles__precio_unitario"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
        return super().get_queryset(request).select_related("cliente", "estado").annotate(_total=Sum(subtotal))

    @admin.display(description="Total", ordering="_total")
    def total(self, obj):
        return _clp(obj._total)

