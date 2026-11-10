"""
Carga los datos semilla de la demo (docs/MODELO_DATOS.md, seccion "Datos semilla").

Es idempotente: los catalogos, productos, camiones y usuarios se crean o actualizan en cada
ejecucion. El historial (pedidos, despachos, prospectos, oportunidades, interacciones) solo
se crea si la tabla de pedidos esta vacia, o si se usa --reset-historial.

    python manage.py seed_demo
    python manage.py seed_demo --reset-historial
"""

import os
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from crm.models import ETAPAS, Cliente, EtapaPipeline, Interaccion, Oportunidad, Prospecto, Vendedor
from cuentas.models import ROLES, Rol, Usuario
from logistica.models import Camion, Despacho
from tienda.models import (
    ESTADO_DESPACHADO,
    ESTADO_EN_PREPARACION,
    ESTADO_ENTREGADO,
    ESTADO_RECHAZADO,
    ESTADO_RECIBIDO,
    ESTADOS,
    TIPO_B2B,
    TIPO_B2C,
    Categoria,
    DetallePedido,
    EstadoPedido,
    ListaPrecio,
    Pedido,
    Producto,
    TipoCliente,
)

CATEGORIAS = [
    ("Carnes congeladas", "-25.0", "-18.0"),
    ("Pescados congelados", "-25.0", "-18.0"),
    ("Lácteos refrigerados", "0.0", "5.0"),
    ("Insumos hospitalarios", "2.0", "8.0"),
    ("Frutas y verduras", "1.0", "8.0"),
]

# sku, nombre, categoria, unidad, stock, precio B2C (B2B = ~15 % menos)
PRODUCTOS = [
    ("CAR-001", "Posta negra de vacuno", "Carnes congeladas", "kg", 800, 11990),
    ("CAR-002", "Pechuga de pollo IQF", "Carnes congeladas", "kg", 1200, 6490),
    ("CAR-003", "Hamburguesa de vacuno (caja 36 u.)", "Carnes congeladas", "caja", 300, 24990),
    ("PES-001", "Filete de salmón atlántico", "Pescados congelados", "kg", 500, 14990),
    ("PES-002", "Merluza austral en filete", "Pescados congelados", "kg", 600, 7990),
    ("PES-003", "Camarón cocido (caja 1 kg)", "Pescados congelados", "caja", 250, 12990),
    ("LAC-001", "Leche entera 1 L (caja 12 u.)", "Lácteos refrigerados", "caja", 400, 13990),
    ("LAC-002", "Yogur natural 125 g (caja 24 u.)", "Lácteos refrigerados", "caja", 350, 9990),
    ("LAC-003", "Queso gauda laminado", "Lácteos refrigerados", "kg", 450, 10990),
    ("HOS-001", "Insulina NPH 10 ml (caja 10 u.)", "Insumos hospitalarios", "caja", 120, 45990),
    ("HOS-002", "Kit de reactivos de laboratorio", "Insumos hospitalarios", "unidad", 80, 89990),
    ("HOS-003", "Vacuna antiinfluenza (caja 10 dosis)", "Insumos hospitalarios", "caja", 150, 59990),
    ("FRU-001", "Arándanos frescos", "Frutas y verduras", "kg", 700, 5990),
    ("FRU-002", "Palta Hass", "Frutas y verduras", "kg", 900, 4490),
    ("FRU-003", "Lechuga hidropónica (caja 12 u.)", "Frutas y verduras", "caja", 200, 8990),
]

DIRECCIONES = [
    "Av. Alemania 0945, Temuco",
    "Calle Montt 870, Temuco",
    "Av. Caupolicán 1200, Temuco",
    "Maquehue 1450, Padre Las Casas",
    "Av. Bernardo O'Higgins 620, Lautaro",
    "Pedro de Valdivia 410, Villarrica",
]

# email, nombre, tipo, rut, telefono, direccion
CLIENTES = [
    ("compras@hospitalregional.cl", "Hospital Regional de Temuco", TIPO_B2B, "61.607.100-5", "+56452551000",
     "Manuel Montt 115, Temuco"),
    ("compras@supermercadoaraucania.cl", "Supermercado Araucanía Ltda.", TIPO_B2B, "76.345.210-8", "+56452410300",
     DIRECCIONES[2]),
    ("abastecimiento@casinoslautaro.cl", "Casinos Escolares Lautaro SpA", TIPO_B2B, "77.120.554-3", "+56452530120",
     DIRECCIONES[4]),
    ("cliente@gmail.com", "María José González", TIPO_B2C, None, "+56987654321", DIRECCIONES[1]),
    ("pedro.salazar@gmail.com", "Pedro Salazar Muñoz", TIPO_B2C, None, "+56976543210", DIRECCIONES[3]),
]

# razon social, rut, contacto, email, telefono, etapa, monto, email del cliente si ya se gano
PROSPECTOS = [
    ("Hotel Lago Villarrica", None, "Andrea Paredes", "compras@hotellagovillarrica.cl", "+56452412000",
     "Prospecto", 2_500_000, None),
    ("Clínica Cautín", "76.888.123-1", "Rodrigo Fuentes", "rfuentes@clinicacautin.cl", "+56452990011",
     "Contactado", 6_800_000, None),
    ("Residencia Adulto Mayor Los Aromos", None, "Patricia Lagos", "plagos@losaromos.cl", None,
     "Cotización enviada", 1_900_000, None),
    ("Supermercado Angol Express", "76.554.002-K", "Luis Cárcamo", "lcarcamo@angolexpress.cl", "+56452711444",
     "Negociación", 4_200_000, None),
    ("Restaurante Fogón del Sur", None, "Claudia Huenchullán", "contacto@fogondelsur.cl", "+56998887766",
     "Negociación", 1_300_000, None),
    ("Hospital Regional de Temuco", "61.607.100-5", "Jorge Sepúlveda", "compras@hospitalregional.cl",
     "+56452551000", "Ganado", 12_000_000, "compras@hospitalregional.cl"),
    ("Pescadería Nueva Imperial", None, "Héctor Millán", "hmillan@pescaderiaimperial.cl", None,
     "Perdido", 900_000, None),
]


class Command(BaseCommand):
    help = "Carga los datos semilla de la demo de Cofrial."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-historial",
            action="store_true",
            help="Borra y regenera pedidos, despachos y datos del CRM (no toca la telemetría).",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        password = os.environ.get("DEMO_PASSWORD")
        if not password or password == "cambia-esto":
            raise CommandError("Define DEMO_PASSWORD en el archivo .env antes de cargar los datos demo.")

        self.rnd = random.Random(2026)
        self._catalogos()
        self._productos()
        self._camiones()
        self._usuarios(password)

        if opts["reset_historial"]:
            self._borrar_historial()
        if Pedido.objects.exists():
            self.stdout.write("Historial ya existe: no se regenera (usa --reset-historial para rehacerlo).")
        else:
            self._crm()
            self._pedidos()

        self._resumen()

    # ------------------------------------------------------------------ catalogos
    def _catalogos(self):
        for nombre in ROLES:
            Rol.objects.get_or_create(nombre=nombre)
        for nombre in (TIPO_B2B, TIPO_B2C):
            TipoCliente.objects.get_or_create(nombre=nombre)
        for nombre in ESTADOS:
            EstadoPedido.objects.get_or_create(nombre=nombre)
        for orden, nombre in enumerate(ETAPAS, start=1):
            EtapaPipeline.objects.update_or_create(nombre=nombre, defaults={"orden": orden})
        for nombre, tmin, tmax in CATEGORIAS:
            Categoria.objects.update_or_create(
                nombre=nombre, defaults={"temp_min": Decimal(tmin), "temp_max": Decimal(tmax)}
            )

    def _productos(self):
        b2b = TipoCliente.objects.get(nombre=TIPO_B2B)
        b2c = TipoCliente.objects.get(nombre=TIPO_B2C)
        categorias = {c.nombre: c for c in Categoria.objects.all()}
        for sku, nombre, cat, unidad, stock, precio_b2c in PRODUCTOS:
            producto, creado = Producto.objects.get_or_create(
                sku=sku,
                defaults={
                    "nombre": nombre,
                    "categoria": categorias[cat],
                    "unidad_medida": unidad,
                    "stock_disponible": stock,
                },
            )
            if not creado:  # no se pisa el stock: puede haber bajado por compras reales
                producto.nombre, producto.categoria, producto.unidad_medida = nombre, categorias[cat], unidad
                producto.save(update_fields=["nombre", "categoria", "unidad_medida"])
            precio_b2b = Decimal(round(precio_b2c * 0.85 / 10) * 10)
            ListaPrecio.objects.update_or_create(producto=producto, tipo=b2c, defaults={"precio": Decimal(precio_b2c)})
            ListaPrecio.objects.update_or_create(producto=producto, tipo=b2b, defaults={"precio": precio_b2b})

    def _camiones(self):
        letras = "BCDFGHJKLPRSTVWXYZ"
        rnd = random.Random(50)
        usadas = set(Camion.objects.values_list("patente", flat=True))
        for i in range(1, 51):
            camion_id = f"CAM-{i:03d}"
            if Camion.objects.filter(camion_id=camion_id).exists():
                continue
            while True:
                patente = "".join(rnd.choice(letras) for _ in range(4)) + f"{rnd.randint(10, 99)}"
                if patente not in usadas:
                    usadas.add(patente)
                    break
            Camion.objects.create(
                camion_id=camion_id, patente=patente, capacidad_kg=rnd.randrange(8000, 12001, 500), activo=True
            )

    def _usuario(self, email, rol, password):
        usuario = Usuario.objects.filter(email=email).first()
        if usuario is None:
            usuario = Usuario(email=email)
        usuario.rol = Rol.objects.get(nombre=rol)
        usuario.activo = True
        usuario.set_password(password)
        usuario.save()
        return usuario

    def _usuarios(self, password):
        self._usuario("admin@cofrial.cl", "administrador", password)
        self._usuario("despacho@cofrial.cl", "despachador", password)
        u_vend = self._usuario("vendedor@cofrial.cl", "vendedor", password)
        self.vendedor, _ = Vendedor.objects.update_or_create(
            usuario=u_vend, defaults={"nombre": "Camila Rojas Henríquez", "telefono": "+56452000111"}
        )
        tipos = {t.nombre: t for t in TipoCliente.objects.all()}
        for email, nombre, tipo, rut, telefono, direccion in CLIENTES:
            usuario = self._usuario(email, "cliente", password)
            Cliente.objects.update_or_create(
                usuario=usuario,
                defaults={
                    "tipo": tipos[tipo],
                    "vendedor": self.vendedor if tipo == TIPO_B2B else None,
                    "nombre_razon_social": nombre,
                    "rut": rut,
                    "telefono": telefono,
                    "direccion_despacho": direccion,
                },
            )

    # ------------------------------------------------------------------ historial
    def _borrar_historial(self):
        Despacho.objects.all().delete()
        DetallePedido.objects.all().delete()
        Pedido.objects.all().delete()
        Interaccion.objects.all().delete()
        Oportunidad.objects.all().delete()
        Prospecto.objects.all().delete()
        self.stdout.write("Historial anterior borrado.")

    def _crm(self):
        ahora = timezone.now()
        etapas = {e.nombre: e for e in EtapaPipeline.objects.all()}
        for i, (razon, rut, contacto, email, tel, etapa, monto, email_cliente) in enumerate(PROSPECTOS):
            cliente = Cliente.objects.filter(usuario__email=email_cliente).first() if email_cliente else None
            prospecto = Prospecto.objects.create(
                vendedor=self.vendedor, cliente=cliente, razon_social=razon, rut=rut,
                contacto=contacto, email=email, telefono=tel,
            )
            creada = ahora - timedelta(days=30 - i * 3)
            cerrada = etapa in ("Ganado", "Perdido")
            oportunidad = Oportunidad.objects.create(
                prospecto=prospecto,
                etapa=etapas[etapa],
                monto_estimado=Decimal(monto),
                fecha_creacion=creada,
                fecha_cierre=creada + timedelta(days=12) if cerrada else None,
            )
            Interaccion.objects.create(
                oportunidad=oportunidad, tipo="llamada",
                detalle=f"Primer contacto con {contacto}: interés en abastecimiento de productos refrigerados.",
                fecha=creada + timedelta(hours=2),
            )
            if etapas[etapa].orden >= 3:
                Interaccion.objects.create(
                    oportunidad=oportunidad, tipo="cotización",
                    detalle=f"Se envía cotización por ${monto:,.0f} con lista de precios institucional.".replace(",", "."),
                    fecha=creada + timedelta(days=4),
                )
            if etapa == "Perdido":
                Interaccion.objects.create(
                    oportunidad=oportunidad, tipo="correo",
                    detalle="El cliente informa que continuará con su proveedor actual por precio.",
                    fecha=creada + timedelta(days=12),
                )

        hospital = Cliente.objects.get(usuario__email="compras@hospitalregional.cl")
        Interaccion.objects.create(
            cliente=hospital, tipo="reunión",
            detalle="Reunión de postventa: se acuerda despacho semanal de insumos hospitalarios los lunes.",
            fecha=ahora - timedelta(days=5),
        )

    def _pedidos(self):
        rnd = self.rnd
        ahora = timezone.now()
        estados = {e.nombre: e for e in EstadoPedido.objects.all()}
        clientes = list(Cliente.objects.select_related("tipo").order_by("id_cliente"))
        productos = list(Producto.objects.order_by("id_producto"))
        precios = {(p.producto_id, p.tipo_id): p.precio for p in ListaPrecio.objects.all()}
        camiones = list(Camion.objects.order_by("camion_id"))
        camiones_en_ruta = iter(camiones[:5])  # los pedidos Despachados usan CAM-001, CAM-002, ...

        # (dias atras, estado): los antiguos ya se entregaron, los recientes siguen en curso
        plan = [
            (13, ESTADO_ENTREGADO), (12, ESTADO_ENTREGADO), (11, ESTADO_RECHAZADO), (10, ESTADO_ENTREGADO),
            (9, ESTADO_ENTREGADO), (8, ESTADO_ENTREGADO), (7, ESTADO_ENTREGADO), (6, ESTADO_ENTREGADO),
            (5, ESTADO_ENTREGADO), (4, ESTADO_ENTREGADO), (3, ESTADO_ENTREGADO), (2, ESTADO_DESPACHADO),
            (1, ESTADO_DESPACHADO), (1, ESTADO_DESPACHADO), (0, ESTADO_DESPACHADO), (0, ESTADO_EN_PREPARACION),
            (0, ESTADO_RECIBIDO), (0, ESTADO_RECIBIDO),
        ]
        for n, (dias, estado) in enumerate(plan, start=1):
            cliente = clientes[n % len(clientes)]
            es_b2b = cliente.tipo.nombre == TIPO_B2B
            creado = ahora - timedelta(days=dias, hours=rnd.randint(1, 8), minutes=rnd.randint(0, 59))
            pedido = Pedido.objects.create(
                cliente=cliente,
                estado=estados[estado],
                canal=Pedido.CANAL_VENDEDOR if es_b2b and rnd.random() < 0.4 else Pedido.CANAL_WEB,
                numero_oc=f"OC-2026-{4100 + n}" if es_b2b else None,
                fecha_entrega_solicitada=(creado + timedelta(days=rnd.randint(1, 3))).date(),
                direccion_entrega=cliente.direccion_despacho,
                fecha_creacion=creado,
            )
            for producto in rnd.sample(productos, rnd.randint(1, 4)):
                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=producto,
                    cantidad=rnd.randint(5, 60) if es_b2b else rnd.randint(1, 5),
                    precio_unitario=precios[(producto.id_producto, cliente.tipo_id)],
                )
            if estado in (ESTADO_DESPACHADO, ESTADO_ENTREGADO):
                camion = next(camiones_en_ruta) if estado == ESTADO_DESPACHADO else rnd.choice(camiones[5:])
                salida = creado + timedelta(hours=rnd.randint(6, 20))
                Despacho.objects.create(
                    pedido=pedido,
                    camion=camion,
                    fecha_salida=min(salida, ahora - timedelta(minutes=30)),
                    fecha_entrega=salida + timedelta(hours=rnd.randint(2, 6)) if estado == ESTADO_ENTREGADO else None,
                )

    def _resumen(self):
        filas = [
            ("roles", Rol), ("usuarios", Usuario), ("tipos_cliente", TipoCliente), ("clientes", Cliente),
            ("vendedores", Vendedor), ("categorias", Categoria), ("productos", Producto),
            ("lista_precios", ListaPrecio), ("estados_pedido", EstadoPedido), ("pedidos", Pedido),
            ("detalle_pedidos", DetallePedido), ("prospectos", Prospecto), ("etapas_pipeline", EtapaPipeline),
            ("oportunidades", Oportunidad), ("interacciones", Interaccion), ("camiones", Camion),
            ("despachos", Despacho),
        ]
        self.stdout.write(self.style.SUCCESS("Datos demo cargados:"))
        for nombre, modelo in filas:
            self.stdout.write(f"  {nombre:<16} {modelo.objects.count():>4}")
