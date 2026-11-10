from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now

TIPO_B2B = "B2B"
TIPO_B2C = "B2C"

ESTADO_RECIBIDO = "Recibido"
ESTADO_EN_PREPARACION = "En preparación"
ESTADO_DESPACHADO = "Despachado"
ESTADO_ENTREGADO = "Entregado"
ESTADO_RECHAZADO = "Rechazado"
ESTADOS = (ESTADO_RECIBIDO, ESTADO_EN_PREPARACION, ESTADO_DESPACHADO, ESTADO_ENTREGADO, ESTADO_RECHAZADO)


class TipoCliente(models.Model):
    id_tipo = models.SmallAutoField(primary_key=True)
    nombre = models.CharField(max_length=10, unique=True)

    class Meta:
        db_table = "tipos_cliente"
        verbose_name = "tipo de cliente"
        verbose_name_plural = "tipos de cliente"

    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    id_categoria = models.SmallAutoField(primary_key=True)
    nombre = models.CharField(max_length=60, unique=True)
    temp_min = models.DecimalField(max_digits=4, decimal_places=1)
    temp_max = models.DecimalField(max_digits=4, decimal_places=1)

    class Meta:
        db_table = "categorias"
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        constraints = [
            models.CheckConstraint(condition=Q(temp_max__gt=F("temp_min")), name="categorias_temp_max_gt_min"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.temp_min} a {self.temp_max} °C)"


class Producto(models.Model):
    id_producto = models.BigAutoField(primary_key=True)
    sku = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=120)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, db_column="id_categoria", related_name="productos"
    )
    unidad_medida = models.CharField(max_length=10)
    stock_disponible = models.IntegerField()

    class Meta:
        db_table = "productos"
        verbose_name = "producto"
        verbose_name_plural = "productos"
        constraints = [
            models.CheckConstraint(condition=Q(stock_disponible__gte=0), name="productos_stock_no_negativo"),
        ]

    def __str__(self):
        return f"{self.sku} · {self.nombre}"


class ListaPrecio(models.Model):
    pk = models.CompositePrimaryKey("producto", "tipo")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, db_column="id_producto", related_name="precios")
    tipo = models.ForeignKey(TipoCliente, on_delete=models.PROTECT, db_column="id_tipo", related_name="precios")
    precio = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "lista_precios"
        verbose_name = "precio"
        verbose_name_plural = "lista de precios"
        constraints = [
            models.CheckConstraint(condition=Q(precio__gt=0), name="lista_precios_precio_positivo"),
        ]

    def __str__(self):
        return f"{self.producto_id} / {self.tipo_id}: {self.precio}"


class EstadoPedido(models.Model):
    id_estado = models.SmallAutoField(primary_key=True)
    nombre = models.CharField(max_length=30, unique=True)

    class Meta:
        db_table = "estados_pedido"
        verbose_name = "estado de pedido"
        verbose_name_plural = "estados de pedido"

    def __str__(self):
        return self.nombre


class Pedido(models.Model):
    CANAL_WEB = "web"
    CANAL_VENDEDOR = "vendedor"
    CANALES = [(CANAL_WEB, "Web"), (CANAL_VENDEDOR, "Vendedor")]

    id_pedido = models.BigAutoField(primary_key=True)
    cliente = models.ForeignKey(
        "crm.Cliente", on_delete=models.PROTECT, db_column="id_cliente", related_name="pedidos"
    )
    estado = models.ForeignKey(EstadoPedido, on_delete=models.PROTECT, db_column="id_estado", related_name="pedidos")
    canal = models.CharField(max_length=10, choices=CANALES)
    numero_oc = models.CharField(max_length=30, null=True, blank=True)
    fecha_entrega_solicitada = models.DateField()
    direccion_entrega = models.CharField(max_length=200)
    fecha_creacion = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "pedidos"
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"
        constraints = [
            models.CheckConstraint(condition=Q(canal__in=["web", "vendedor"]), name="pedidos_canal_valido"),
        ]

    def __str__(self):
        return f"Pedido #{self.id_pedido}"


class DetallePedido(models.Model):
    pk = models.CompositePrimaryKey("pedido", "producto")
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, db_column="id_pedido", related_name="detalles")
    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, db_column="id_producto", related_name="detalles"
    )
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "detalle_pedidos"
        verbose_name = "detalle de pedido"
        verbose_name_plural = "detalle de pedidos"
        constraints = [
            models.CheckConstraint(condition=Q(cantidad__gt=0), name="detalle_pedidos_cantidad_positiva"),
        ]

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.pedido_id} · {self.producto_id} x {self.cantidad}"
