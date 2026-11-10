from django.db import models
from django.db.models import Q
from django.db.models.functions import Now


class Camion(models.Model):
    camion_id = models.CharField(max_length=10, primary_key=True)
    patente = models.CharField(max_length=8, unique=True)
    capacidad_kg = models.IntegerField()
    activo = models.BooleanField(default=True, db_default=True)

    class Meta:
        db_table = "camiones"
        ordering = ["camion_id"]
        verbose_name = "camión"
        verbose_name_plural = "camiones"

    def __str__(self):
        return f"{self.camion_id} ({self.patente})"


class Despacho(models.Model):
    id_despacho = models.BigAutoField(primary_key=True)
    pedido = models.OneToOneField(
        "tienda.Pedido", on_delete=models.CASCADE, db_column="id_pedido", related_name="despacho"
    )
    camion = models.ForeignKey(Camion, on_delete=models.PROTECT, db_column="camion_id", related_name="despachos")
    fecha_salida = models.DateTimeField()
    fecha_entrega = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "despachos"
        verbose_name = "despacho"
        verbose_name_plural = "despachos"

    def __str__(self):
        return f"Despacho #{self.id_despacho} · {self.camion_id}"


class TelemetriaRuta(models.Model):
    """Lecturas IoT. El simulador inserta aqui con SQL directo (nombres de columna exigidos por la rubrica)."""

    id_telemetria = models.BigAutoField(primary_key=True)
    camion = models.ForeignKey(Camion, on_delete=models.CASCADE, db_column="camion_id", related_name="lecturas")
    temp_camara = models.FloatField()
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    long = models.DecimalField(max_digits=9, decimal_places=6)
    combustible_pct = models.IntegerField()
    alerta_ruptura_frio = models.BooleanField(default=False, db_default=False)
    fecha_hora = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "telemetria_ruta"
        verbose_name = "lectura de telemetría"
        verbose_name_plural = "telemetría de ruta"
        indexes = [
            models.Index(fields=["camion", "-fecha_hora"], name="telemetria_camion_fecha_idx"),
            models.Index(fields=["-fecha_hora"], name="telemetria_fecha_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(lat__gte=-90, lat__lte=90), name="telemetria_lat_rango"),
            models.CheckConstraint(condition=Q(long__gte=-180, long__lte=180), name="telemetria_long_rango"),
            models.CheckConstraint(
                condition=Q(combustible_pct__gte=0, combustible_pct__lte=100), name="telemetria_combustible_rango"
            ),
        ]

    def __str__(self):
        return f"{self.camion_id} · {self.temp_camara} °C"
