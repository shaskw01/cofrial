# Modelo de datos (fuente de verdad)

Este es el modelo 3FN del Informe Hito 1 (Figura 2 y Tabla 4), con 2 ajustes de coherencia ya aprobados:
- `pedidos` incluye `numero_oc`, `fecha_entrega_solicitada` y `direccion_entrega`.
- `interacciones` puede ligarse a una oportunidad **o** a un cliente (`CHECK id_oportunidad IS NOT NULL OR id_cliente IS NOT NULL`).

Reglas de implementación:
- Base de datos: **PostgreSQL 16** (Amazon RDS en producción, contenedor `postgres:16` en local).
- Las tablas se crean con **migraciones de Django**. Cada modelo usa `Meta.db_table` con el nombre en minúsculas de la tabla (ej. `telemetria_ruta`), para que el simulador IoT pueda insertar con SQL directo.
- No renombrar columnas: los campos de telemetría (`camion_id`, `temp_camara`, `lat`, `long`, `combustible_pct`, `alerta_ruptura_frio`) son exigidos por la rúbrica con esos nombres exactos.
- `Usuarios`: usar un modelo de usuario personalizado de Django (`AUTH_USER_MODEL`) con `email` como login y FK a `roles`. `password_hash` corresponde al campo `password` de Django.
- El subtotal de una línea NO se guarda: se calcula `cantidad * precio_unitario`.

## roles  (Seguridad)
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id_rol` | SMALLSERIAL | PK | Identificador del rol. |
| `nombre` | VARCHAR(30) | NOT NULL, UNIQUE | Rol del sistema: administrador, vendedor, despachador, cliente. |

## usuarios  (Seguridad)
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id_usuario` | BIGSERIAL | PK | Identificador de la cuenta de acceso. |
| `email` | VARCHAR(120) | NOT NULL, UNIQUE | Correo usado para iniciar sesión. |
| `password_hash` | VARCHAR(255) | NOT NULL | Contraseña cifrada (hash), nunca en texto plano. |
| `id_rol` | SMALLINT | FK → Roles, NOT NULL | Rol que define los permisos del usuario. |
| `activo` | BOOLEAN | NOT NULL, DEFAULT TRUE | Permite deshabilitar una cuenta sin borrarla. |
| `fecha_creacion` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Fecha y hora de registro. |

## tipos_cliente  (E-commerce)
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id_tipo` | SMALLSERIAL | PK | Identificador del perfil comercial. |
| `nombre` | VARCHAR(10) | NOT NULL, UNIQUE | Perfil: B2B (institucional) o B2C (público general). |

## clientes  (E-commerce)
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id_cliente` | BIGSERIAL | PK | Identificador del cliente. |
| `id_usuario` | BIGINT | FK → Usuarios, NOT NULL, UNIQUE | Cuenta con la que el cliente compra en el portal. |
| `id_tipo` | SMALLINT | FK → Tipos_Cliente, NOT NULL | Perfil B2B o B2C; define la lista de precios. |
| `id_vendedor` | BIGINT | FK → Vendedores, NULL | Vendedor asignado (obligatorio para B2B). |
| `nombre_razon_social` | VARCHAR(150) | NOT NULL | Razón social (B2B) o nombre completo (B2C). |
| `rut` | VARCHAR(12) | UNIQUE, NULL | RUT de la empresa o persona; obligatorio para B2B. |
| `telefono` | VARCHAR(20) | NOT NULL | Teléfono de contacto. |
| `direccion_despacho` | VARCHAR(200) | NOT NULL | Dirección de entrega de los pedidos. |

## categorias  (E-commerce)
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id_categoria` | SMALLSERIAL | PK | Identificador de la categoría. |
| `nombre` | VARCHAR(60) | NOT NULL, UNIQUE | Ej.: carnes congeladas, lácteos, insumos hospitalarios. |
| `temp_min` | NUMERIC(4,1) | NOT NULL | Temperatura mínima de conservación (°C). |
| `temp_max` | NUMERIC(4,1) | NOT NULL, CHECK (temp_max > temp_min) | Temperatura máxima de conservación (°C); sobre este valor se activa la alerta. |

## productos  (E-commerce)
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id_producto` | BIGSERIAL | PK | Identificador del producto. |
| `sku` | VARCHAR(30) | NOT NULL, UNIQUE | Código interno del producto. |
| `nombre` | VARCHAR(120) | NOT NULL | Nombre comercial. |
| `id_categoria` | SMALLINT | FK → Categorias, NOT NULL | Categoría que define el rango de temperatura. |
| `unidad_medida` | VARCHAR(10) | NOT NULL | kg, caja o unidad. |
| `stock_disponible` | INTEGER | NOT NULL, CHECK (≥ 0) | Existencias reales; se descuentan al confirmar un pedido. |

## lista_precios  (E-commerce)
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id_producto` | BIGINT | PK compuesta, FK → Productos | Producto al que aplica el precio. |
| `id_tipo` | SMALLINT | PK compuesta, FK → Tipos_Cliente | Perfil B2B o B2C. |
| `precio` | NUMERIC(12,2) | NOT NULL, CHECK (> 0) | Precio neto del producto para ese perfil. |

## estados_pedido  (E-commerce)
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id_estado` | SMALLSERIAL | PK | Identificador del estado. |
| `nombre` | VARCHAR(30) | NOT NULL, UNIQUE | Recibido, En preparación, Despachado, Entregado, Rechazado. |

## pedidos  (E-commerce)
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id_pedido` | BIGSERIAL | PK | Identificador de la orden de compra. |
| `id_cliente` | BIGINT | FK → Clientes, NOT NULL | Cliente que realiza el pedido. |
| `id_estado` | SMALLINT | FK → Estados_Pedido, NOT NULL | Estado actual del pedido (postventa). |
| `canal` | VARCHAR(10) | NOT NULL, CHECK (web, vendedor) | Canal de ingreso; permite medir el % de pedidos digitales. |
| `numero_oc` | VARCHAR(30) | NULL | N.º de orden de compra institucional (solo B2B). |
| `fecha_entrega_solicitada` | DATE | NOT NULL | Fecha de despacho elegida por el cliente en el carrito. |
| `direccion_entrega` | VARCHAR(200) | NOT NULL | Dirección de entrega de este pedido (por defecto, la del cliente). |
| `fecha_creacion` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Fecha y hora del pedido. |

## detalle_pedidos  (E-commerce)
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id_pedido` | BIGINT | PK compuesta, FK → Pedidos | Pedido al que pertenece la línea. |
| `id_producto` | BIGINT | PK compuesta, FK → Productos | Producto solicitado. |
| `cantidad` | INTEGER | NOT NULL, CHECK (> 0) | Unidades solicitadas. |
| `precio_unitario` | NUMERIC(12,2) | NOT NULL | Precio vigente al momento de la compra (historial). El subtotal se calcula, no se almacena. |

## vendedores  (CRM)
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id_vendedor` | BIGSERIAL | PK | Identificador del vendedor. |
| `id_usuario` | BIGINT | FK → Usuarios, NOT NULL, UNIQUE | Cuenta de acceso al CRM. |
| `nombre` | VARCHAR(100) | NOT NULL | Nombre del vendedor. |
| `telefono` | VARCHAR(20) | NOT NULL | Teléfono corporativo. |

## prospectos  (CRM)
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id_prospecto` | BIGSERIAL | PK | Identificador del prospecto (posible cliente). |
| `id_vendedor` | BIGINT | FK → Vendedores, NOT NULL | Vendedor responsable del prospecto. |
| `id_cliente` | BIGINT | FK → Clientes, NULL, UNIQUE | Se completa cuando el prospecto se convierte en cliente. |
| `razon_social` | VARCHAR(150) | NOT NULL | Empresa o institución prospectada. |
| `rut` | VARCHAR(12) | NULL | RUT, si se conoce. |
| `contacto` | VARCHAR(100) | NOT NULL | Persona de contacto. |
| `email` | VARCHAR(120) | NOT NULL | Correo de contacto. |
| `telefono` | VARCHAR(20) | NULL | Teléfono de contacto. |

## etapas_pipeline  (CRM)
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id_etapa` | SMALLSERIAL | PK | Identificador de la etapa. |
| `nombre` | VARCHAR(30) | NOT NULL, UNIQUE | Prospecto, Contactado, Cotización enviada, Negociación, Ganado, Perdido. |
| `orden` | SMALLINT | NOT NULL | Posición de la columna en el tablero Kanban. |

## oportunidades  (CRM)
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id_oportunidad` | BIGSERIAL | PK | Identificador de la oportunidad de venta. |
| `id_prospecto` | BIGINT | FK → Prospectos, NOT NULL | Prospecto asociado (y, a través de él, el vendedor). |
| `id_etapa` | SMALLINT | FK → Etapas_Pipeline, NOT NULL | Etapa actual en el pipeline comercial. |
| `monto_estimado` | NUMERIC(12,2) | NOT NULL | Valor estimado del negocio. |
| `fecha_creacion` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Inicio de la oportunidad. |
| `fecha_cierre` | TIMESTAMPTZ | NULL | Fecha en que se ganó o perdió. |

## interacciones  (CRM)
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id_interaccion` | BIGSERIAL | PK | Identificador de la interacción. |
| `id_oportunidad` | BIGINT | FK → Oportunidades, NULL | Oportunidad comercial asociada, si existe. |
| `id_cliente` | BIGINT | FK → Clientes, NULL, CHECK (id_oportunidad o id_cliente no nulo) | Cliente activo asociado (postventa o reclamo). |
| `tipo` | VARCHAR(20) | NOT NULL | Llamada, correo, reunión, cotización o reclamo. |
| `detalle` | TEXT | NOT NULL | Resumen de lo conversado o acordado. |
| `fecha` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Fecha y hora de la interacción. |

## camiones  (Logística IoT)
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `camion_id` | VARCHAR(10) | PK | Código de la unidad (ej.: CAM-001). |
| `patente` | VARCHAR(8) | NOT NULL, UNIQUE | Patente del vehículo. |
| `capacidad_kg` | INTEGER | NOT NULL | Capacidad de carga. |
| `activo` | BOOLEAN | NOT NULL, DEFAULT TRUE | Indica si el camión está operativo. |

## despachos  (Logística IoT)
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id_despacho` | BIGSERIAL | PK | Identificador del despacho. |
| `id_pedido` | BIGINT | FK → Pedidos, NOT NULL, UNIQUE | Pedido que se despacha. |
| `camion_id` | VARCHAR(10) | FK → Camiones, NOT NULL | Camión asignado. |
| `fecha_salida` | TIMESTAMPTZ | NOT NULL | Salida desde bodega. |
| `fecha_entrega` | TIMESTAMPTZ | NULL | Entrega confirmada; NULL mientras está en ruta. |

## telemetria_ruta  (Logística IoT)
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id_telemetria` | BIGSERIAL | PK | Identificador del registro IoT. |
| `camion_id` | VARCHAR(10) | FK → Camiones, NOT NULL | Unidad que envía la lectura. |
| `temp_camara` | DOUBLE PRECISION | NOT NULL | Temperatura de la cámara de frío (°C). |
| `lat` | NUMERIC(9,6) | NOT NULL, CHECK (-90 a 90) | Latitud de la posición. |
| `long` | NUMERIC(9,6) | NOT NULL, CHECK (-180 a 180) | Longitud de la posición. |
| `combustible_pct` | INTEGER | NOT NULL, CHECK (0 a 100) | Nivel de estanque en porcentaje. |
| `alerta_ruptura_frio` | BOOLEAN | NOT NULL, DEFAULT FALSE | TRUE si temp_camara salió del rango de conservación. |
| `fecha_hora` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Momento de la lectura. |

## Relaciones

- roles 1—N usuarios
- usuarios 1—0..1 clientes; usuarios 1—0..1 vendedores
- tipos_cliente 1—N clientes; tipos_cliente 1—N lista_precios
- vendedores 0..1—N clientes (vendedor asignado); vendedores 1—N prospectos
- categorias 1—N productos; productos 1—N lista_precios; productos 1—N detalle_pedidos
- clientes 1—N pedidos; estados_pedido 1—N pedidos; pedidos 1—N detalle_pedidos
- prospectos 0..1—0..1 clientes (al ganar la oportunidad); prospectos 1—N oportunidades
- etapas_pipeline 1—N oportunidades; oportunidades 0..1—N interacciones; clientes 0..1—N interacciones
- pedidos 1—0..1 despachos; camiones 1—N despachos; camiones 1—N telemetria_ruta

## Datos semilla (comando `python manage.py seed_demo`)

- roles: administrador, vendedor, despachador, cliente
- tipos_cliente: B2B, B2C
- estados_pedido: Recibido, En preparación, Despachado, Entregado, Rechazado
- etapas_pipeline (orden): Prospecto 1, Contactado 2, Cotización enviada 3, Negociación 4, Ganado 5, Perdido 6
- categorias: Carnes congeladas (-25,0 a -18,0 °C), Pescados congelados (-25,0 a -18,0), Lácteos refrigerados (0,0 a 5,0), Insumos hospitalarios (2,0 a 8,0), Frutas y verduras (1,0 a 8,0)
- productos: 12 a 15 productos repartidos en las categorías, con stock inicial y precios en lista_precios para B2B (neto, más bajo) y B2C
- camiones: CAM-001 a CAM-050, patentes ficticias, capacidad 8000 a 12000 kg
- usuarios demo: admin@cofrial.cl, vendedor@cofrial.cl, despacho@cofrial.cl, compras@hospitalregional.cl (B2B), cliente@gmail.com (B2C). Contraseña demo en `.env` (`DEMO_PASSWORD`), nunca en el código.
- CRM: 6 a 8 prospectos con oportunidades repartidas en todas las etapas, y 10 a 20 pedidos históricos de los últimos 14 días para que el dashboard tenga datos desde el primer minuto.
