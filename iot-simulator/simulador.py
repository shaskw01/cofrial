"""
Simulador IoT de la flota de Cofrial.

Cada INTERVALO_SEG inserta en `telemetria_ruta` una lectura por cada camion del rango
CAMION_DESDE..CAMION_HASTA (CAM-001, CAM-002, ...), con SQL directo sobre PostgreSQL (RDS):

    camion_id (string), temp_camara (float), lat / long, combustible_pct (integer),
    alerta_ruptura_frio (boolean)

Regla de la alerta: `alerta_ruptura_frio = TRUE` cuando `temp_camara` esta fuera del rango
[temp_min, temp_max] de la carga. Con un despacho activo, el rango es el mas estricto entre las
categorias de los productos del pedido; sin despacho, el de Carnes congeladas.
"""

import logging
import math
import os
import random
import signal
import sys
import time

import psycopg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("simulador")

CAMION_DESDE = int(os.environ.get("CAMION_DESDE", "1"))
CAMION_HASTA = int(os.environ.get("CAMION_HASTA", "10"))
INTERVALO_SEG = float(os.environ.get("INTERVALO_SEG", "5"))
PROB_FALLA = float(os.environ.get("PROB_FALLA", "0.02"))

BODEGA = (-38.7359, -72.5904)  # Temuco
DESTINOS = {
    "Padre Las Casas": (-38.7667, -72.6000),
    "Lautaro": (-38.5317, -72.4361),
    "Villarrica": (-39.2857, -72.2279),
    "Angol": (-37.7952, -72.7164),
    "Nueva Imperial": (-38.7447, -72.9510),
}
VELOCIDAD_KMH = 60

# Rango de conservacion por camion. Despacho activo = sin fecha de entrega y pedido en estado Despachado.
# Si la carga mezcla categorias sin rango comun (congelado + refrigerado), manda la mas fria.
SQL_RANGOS = """
WITH base AS (
    SELECT temp_min, temp_max FROM categorias WHERE nombre = 'Carnes congeladas'
),
carga AS (
    SELECT d.camion_id,
           max(c.temp_min) AS estricto_min,
           min(c.temp_max) AS estricto_max,
           (array_agg(c.temp_min ORDER BY c.temp_max, c.temp_min))[1] AS frio_min,
           min(c.temp_max) AS frio_max
    FROM despachos d
    JOIN pedidos p ON p.id_pedido = d.id_pedido
    JOIN estados_pedido e ON e.id_estado = p.id_estado
    JOIN detalle_pedidos dp ON dp.id_pedido = p.id_pedido
    JOIN productos pr ON pr.id_producto = dp.id_producto
    JOIN categorias c ON c.id_categoria = pr.id_categoria
    WHERE d.fecha_entrega IS NULL AND e.nombre = 'Despachado'
    GROUP BY d.camion_id
)
SELECT cam.camion_id,
       CASE WHEN carga.camion_id IS NULL THEN base.temp_min
            WHEN carga.estricto_min < carga.estricto_max THEN carga.estricto_min
            ELSE carga.frio_min END::float8,
       CASE WHEN carga.camion_id IS NULL THEN base.temp_max
            WHEN carga.estricto_min < carga.estricto_max THEN carga.estricto_max
            ELSE carga.frio_max END::float8,
       carga.camion_id IS NOT NULL
FROM camiones cam
CROSS JOIN base
LEFT JOIN carga ON carga.camion_id = cam.camion_id
WHERE cam.activo AND cam.camion_id = ANY(%s)
ORDER BY cam.camion_id
"""

SQL_INSERTAR = """
INSERT INTO telemetria_ruta (camion_id, temp_camara, lat, "long", combustible_pct, alerta_ruptura_frio)
VALUES (%s, %s, %s, %s, %s, %s)
"""


def distancia_km(a, b):
    """Distancia aproximada entre dos puntos (lat, long) cercanos."""
    dlat = (b[0] - a[0]) * 111.0
    dlon = (b[1] - a[1]) * 111.0 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot(dlat, dlon)


class Camion:
    """Estado simulado de un camion: ruta, combustible y camara de frio."""

    def __init__(self, camion_id: str):
        self.camion_id = camion_id
        self.rnd = random.Random(f"{camion_id}-{time.time_ns()}")
        numero = int(camion_id.split("-")[1])
        self.destino_nombre = list(DESTINOS)[numero % len(DESTINOS)]
        self.destino = DESTINOS[self.destino_nombre]
        self.largo_km = max(distancia_km(BODEGA, self.destino), 1.0)
        self.avance = self.rnd.random()  # 0 = bodega, 1 = destino
        self.sentido = self.rnd.choice((1, -1))
        self.combustible = self.rnd.uniform(35, 100)
        self.rango = None
        self.temp = None
        self.falla_restante = 0  # lecturas que le quedan a la falla de frio en curso

    def fijar_rango(self, temp_min: float, temp_max: float):
        if self.rango != (temp_min, temp_max):
            # Carga nueva: la camara parte estabilizada en el centro de su rango.
            self.rango = (temp_min, temp_max)
            self.temp = (temp_min + temp_max) / 2 + self.rnd.uniform(-0.5, 0.5)
            self.falla_restante = 0

    def _mover(self):
        paso = VELOCIDAD_KMH * self.rnd.uniform(0.6, 1.2) * INTERVALO_SEG / 3600 / self.largo_km
        self.avance += paso * self.sentido
        if self.avance >= 1:
            self.avance, self.sentido = 1.0, -1
        elif self.avance <= 0:
            self.avance, self.sentido = 0.0, 1
        lat = BODEGA[0] + (self.destino[0] - BODEGA[0]) * self.avance + self.rnd.gauss(0, 0.0003)
        lon = BODEGA[1] + (self.destino[1] - BODEGA[1]) * self.avance + self.rnd.gauss(0, 0.0003)
        return round(lat, 6), round(lon, 6)

    def _combustible(self):
        self.combustible -= self.rnd.uniform(0.02, 0.08) * INTERVALO_SEG / 5
        if self.combustible <= 8:
            self.combustible = self.rnd.uniform(92, 100)  # recarga
        return int(round(self.combustible))

    def _temperatura(self):
        temp_min, temp_max = self.rango
        centro = (temp_min + temp_max) / 2
        margen = (temp_max - temp_min) * 0.3
        if self.falla_restante == 0 and self.temp <= temp_max and self.rnd.random() < PROB_FALLA:
            self.falla_restante = self.rnd.randint(4, 9)

        if self.falla_restante > 0:
            # Falla del equipo de frio: la temperatura sube lectura a lectura.
            self.falla_restante -= 1
            self.temp += self.rnd.uniform(0.9, 1.8)
        elif self.temp > centro + margen:
            # Recuperacion: el equipo vuelve a enfriar hasta la zona normal.
            self.temp -= self.rnd.uniform(1.0, 2.0)
        else:
            # Operacion normal: oscila cerca del centro del rango, sin salirse.
            self.temp += (centro - self.temp) * 0.2 + self.rnd.gauss(0, 0.12)
            self.temp = min(max(self.temp, centro - margen), centro + margen)
        return round(self.temp, 2)

    def lectura(self):
        lat, lon = self._mover()
        temp = self._temperatura()
        alerta = not (self.rango[0] <= temp <= self.rango[1])
        return (self.camion_id, temp, lat, lon, self._combustible(), alerta)


def conectar():
    """Abre la conexion a PostgreSQL; reintenta hasta que la base responda."""
    espera = 2
    while True:
        try:
            conexion = psycopg.connect(
                host=os.environ["DB_HOST"],
                port=os.environ.get("DB_PORT", "5432"),
                dbname=os.environ["DB_NAME"],
                user=os.environ["DB_USER"],
                password=os.environ["DB_PASSWORD"],
                connect_timeout=10,
                autocommit=True,
                application_name=f"simulador-iot-{CAMION_DESDE:03d}-{CAMION_HASTA:03d}",
            )
            log.info("Conectado a la base de datos %s en %s", os.environ["DB_NAME"], os.environ["DB_HOST"])
            return conexion
        except psycopg.OperationalError as e:
            log.warning("La base de datos no responde (%s). Reintento en %s s", str(e).strip().splitlines()[0], espera)
            time.sleep(espera)
            espera = min(espera * 2, 30)


def ciclo(conexion, camiones: dict, ids: list[str]) -> str:
    """Lee los rangos vigentes, genera una lectura por camion y las inserta. Devuelve el resumen para el log."""
    with conexion.cursor() as cur:
        cur.execute(SQL_RANGOS, (ids,))
        filas = cur.fetchall()
        if not filas:
            return "Sin camiones activos en este rango (¿falta correr seed_demo?). No se inserta nada."

        lecturas = []
        en_ruta = 0
        for camion_id, temp_min, temp_max, con_despacho in filas:
            camion = camiones.setdefault(camion_id, Camion(camion_id))
            camion.fijar_rango(temp_min, temp_max)
            lecturas.append(camion.lectura())
            en_ruta += con_despacho
        cur.executemany(SQL_INSERTAR, lecturas)

    alertas = [f"{l[0]} {l[1]:.1f} °C" for l in lecturas if l[5]]
    resumen = f"{len(lecturas)} lecturas insertadas en telemetria_ruta, {en_ruta} con despacho en ruta"
    if alertas:
        resumen += f", ALERTA de ruptura de frio en {', '.join(alertas)}"
    return resumen


def main():
    ids = [f"CAM-{n:03d}" for n in range(CAMION_DESDE, CAMION_HASTA + 1)]
    log.info(
        "Simulador IoT: camiones %s a %s, una lectura cada %s s, probabilidad de falla %s",
        ids[0], ids[-1], INTERVALO_SEG, PROB_FALLA,
    )
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    camiones: dict[str, Camion] = {}
    conexion = conectar()
    while True:
        inicio = time.monotonic()
        try:
            log.info(ciclo(conexion, camiones, ids))
        except psycopg.OperationalError as e:
            log.warning("Se perdio la conexion (%s). Reconectando", str(e).strip().splitlines()[0])
            try:
                conexion.close()
            except Exception:
                pass
            conexion = conectar()
        except psycopg.Error as e:
            log.error("Error al insertar (%s). Se reintenta en el proximo ciclo", str(e).strip().splitlines()[0])
        time.sleep(max(0.0, INTERVALO_SEG - (time.monotonic() - inicio)))


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        log.info("Simulador detenido")
