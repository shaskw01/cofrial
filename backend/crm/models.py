from django.db import models
from django.db.models import Q
from django.db.models.functions import Now

ETAPA_PROSPECTO = "Prospecto"
ETAPA_CONTACTADO = "Contactado"
ETAPA_COTIZACION = "Cotización enviada"
ETAPA_NEGOCIACION = "Negociación"
ETAPA_GANADO = "Ganado"
ETAPA_PERDIDO = "Perdido"
ETAPAS = (ETAPA_PROSPECTO, ETAPA_CONTACTADO, ETAPA_COTIZACION, ETAPA_NEGOCIACION, ETAPA_GANADO, ETAPA_PERDIDO)


class Vendedor(models.Model):
    id_vendedor = models.BigAutoField(primary_key=True)
    usuario = models.OneToOneField(
        "cuentas.Usuario", on_delete=models.PROTECT, db_column="id_usuario", related_name="vendedor"
    )
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20)

    class Meta:
        db_table = "vendedores"
        verbose_name = "vendedor"
        verbose_name_plural = "vendedores"

    def __str__(self):
        return self.nombre


class Cliente(models.Model):
    id_cliente = models.BigAutoField(primary_key=True)
    usuario = models.OneToOneField(
        "cuentas.Usuario", on_delete=models.PROTECT, db_column="id_usuario", related_name="cliente"
    )
    tipo = models.ForeignKey(
        "tienda.TipoCliente", on_delete=models.PROTECT, db_column="id_tipo", related_name="clientes"
    )
    vendedor = models.ForeignKey(
        Vendedor, on_delete=models.SET_NULL, null=True, blank=True, db_column="id_vendedor", related_name="clientes"
    )
    nombre_razon_social = models.CharField(max_length=150)
    rut = models.CharField(max_length=12, unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=20)
    direccion_despacho = models.CharField(max_length=200)

    class Meta:
        db_table = "clientes"
        verbose_name = "cliente"
        verbose_name_plural = "clientes"

    def __str__(self):
        return self.nombre_razon_social


class Prospecto(models.Model):
    id_prospecto = models.BigAutoField(primary_key=True)
    vendedor = models.ForeignKey(
        Vendedor, on_delete=models.PROTECT, db_column="id_vendedor", related_name="prospectos"
    )
    cliente = models.OneToOneField(
        Cliente, on_delete=models.SET_NULL, null=True, blank=True, db_column="id_cliente", related_name="prospecto"
    )
    razon_social = models.CharField(max_length=150)
    rut = models.CharField(max_length=12, null=True, blank=True)
    contacto = models.CharField(max_length=100)
    email = models.EmailField(max_length=120)
    telefono = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = "prospectos"
        verbose_name = "prospecto"
        verbose_name_plural = "prospectos"

    def __str__(self):
        return self.razon_social


class EtapaPipeline(models.Model):
    id_etapa = models.SmallAutoField(primary_key=True)
    nombre = models.CharField(max_length=30, unique=True)
    orden = models.SmallIntegerField()

    class Meta:
        db_table = "etapas_pipeline"
        ordering = ["orden"]
        verbose_name = "etapa del pipeline"
        verbose_name_plural = "etapas del pipeline"

    def __str__(self):
        return self.nombre


class Oportunidad(models.Model):
    id_oportunidad = models.BigAutoField(primary_key=True)
    prospecto = models.ForeignKey(
        Prospecto, on_delete=models.CASCADE, db_column="id_prospecto", related_name="oportunidades"
    )
    etapa = models.ForeignKey(
        EtapaPipeline, on_delete=models.PROTECT, db_column="id_etapa", related_name="oportunidades"
    )
    monto_estimado = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_creacion = models.DateTimeField(db_default=Now())
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "oportunidades"
        verbose_name = "oportunidad"
        verbose_name_plural = "oportunidades"

    def __str__(self):
        return f"Oportunidad #{self.id_oportunidad} · {self.prospecto}"


class Interaccion(models.Model):
    id_interaccion = models.BigAutoField(primary_key=True)
    oportunidad = models.ForeignKey(
        Oportunidad,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_column="id_oportunidad",
        related_name="interacciones",
    )
    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE, null=True, blank=True, db_column="id_cliente", related_name="interacciones"
    )
    tipo = models.CharField(max_length=20)
    detalle = models.TextField()
    fecha = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "interacciones"
        ordering = ["-fecha"]
        verbose_name = "interacción"
        verbose_name_plural = "interacciones"
        constraints = [
            models.CheckConstraint(
                condition=Q(oportunidad__isnull=False) | Q(cliente__isnull=False),
                name="interacciones_oportunidad_o_cliente",
            ),
        ]

    def __str__(self):
        return f"{self.tipo} · {self.fecha:%d-%m-%Y}" if self.fecha else self.tipo
