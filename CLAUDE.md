# Cofrial SpA — Prototipo de Transformación Digital (Hito 2)

Proyecto grupal de la asignatura **Transformación Digital (TIEL15), INACAP Temuco**.
Entrega y defensa en vivo: **jueves 12 de noviembre de 2026**.

El diseño ya fue aprobado en el Informe Hito 1. Este repositorio implementa ese diseño. Si algo no está definido aquí ni en `docs/`, pregunta antes de inventarlo.

## Cómo trabajar en este proyecto

- Responde y escribe la interfaz en **español de Chile**. Código, nombres de variables y commits en español sin tildes o en inglés técnico, pero consistentes.
- Trabaja **una fase a la vez** según `docs/PLAN.md`. Al terminar una fase: muestra cómo probarla, espera confirmación del usuario y recién ahí avanza.
- Antes de cambios grandes, explica el plan en 3 a 5 líneas.
- Nunca escribas secretos en el código. Todo va en `.env` (ignorado por git). Mantén `.env.example` actualizado.
- Después de cada fase, haz `git commit` con un mensaje claro.
- El modelo de datos es fijo: **@docs/MODELO_DATOS.md**. No renombres tablas ni columnas sin preguntar.

## Rúbrica del Hito 2 (lo que se evalúa)

Cada dimensión vale 100% (Logrado), 60% (Medianamente) o 0%. Lo que define "Logrado":

1. **Despliegue en AWS Academy**: EC2 operativas con el backend corriendo de forma persistente, conectadas a **Amazon RDS**. Se penaliza si depende del computador local.
2. **E-commerce y CRM operativo**: catálogo de productos refrigerados, selección de perfil **B2B (lista de precios institucional) / B2C**, carrito, generación de órdenes, y un **CRM conectado** a la BD para gestionar clientes, prospectos y seguimiento de pedidos. Se penaliza con 60% si son maquetas HTML sin backend.
3. **Simulación IoT con Docker en EC2**: contenedores en un **nodo EC2 dedicado** que inyectan **automáticamente** a RDS: `camion_id` (string), `temp_camara` (float), `lat`/`long`, `combustible_pct` (integer), `alerta_ruptura_frio` (boolean). Inserciones manuales o Excel = 60%.
4. **Dashboard BI en vivo**: conectado a la BD de la nube, que **cruce** métricas comerciales (ventas, pedidos por canal) con las alertas de cadena de frío IoT. Gráficos estáticos = 60%.
5. **IA costo cero + defensa**: una API pública de IA gratuita integrada en el CRM o el E-commerce para atender clientes o clasificar requerimientos, y demostrar todo funcionando en vivo.

## Arquitectura (Figura 1 del informe)

```
Internet ── IGW ── VPC 10.0.0.0/16 (us-east-1)
  Subred pública 10.0.1.0/24 (us-east-1a)
    EC2 Front-Office t3.small + Elastic IP   SG-Web: 80/443 abierto, 22 solo IP admin
      docker compose: nginx (build React + proxy /api) → django (gunicorn :8000)
    EC2 Back-Office IoT t3.micro             SG-IoT: solo 22 desde IP admin
      docker compose: 5 contenedores simuladores (10 camiones cada uno)
  Subred privada A 10.0.3.0/24 (us-east-1a)  RDS PostgreSQL 16 db.t3.micro, sin acceso público
  Subred privada B 10.0.4.0/24 (us-east-1b)  (completa el DB Subnet Group)
  SG-RDS: 5432 solo desde SG-Web y SG-IoT
IA: Front-Office llama por HTTPS saliente a Groq (API compatible con OpenAI, capa gratuita)
```

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12, Django 5, Django REST Framework, `psycopg` 3, gunicorn, `django-cors-headers`, autenticación por token (DRF `TokenAuthentication` o SimpleJWT) |
| Frontend | React + Vite, React Router, Tailwind CSS, Recharts (gráficos), Leaflet + OpenStreetMap (mapa de camiones, opcional) |
| Base de datos | PostgreSQL 16 (RDS en AWS; contenedor `postgres:16` solo para desarrollo local) |
| IoT | Python 3.12 + `psycopg` 3, en contenedores Docker |
| IA | Groq API (`https://api.groq.com/openai/v1`), modelo configurable por `GROQ_MODEL` |
| Despliegue | Docker Compose en cada EC2, nginx como servidor web y proxy inverso |

## Estructura del repositorio

```
cofrial/
├── CLAUDE.md
├── docs/                 PLAN.md, MODELO_DATOS.md, AWS_SETUP.md, DEMO.md
├── backend/              proyecto Django "cofrial"
│   ├── cofrial/          settings (lee todo desde variables de entorno)
│   ├── cuentas/          roles, usuarios (AUTH_USER_MODEL), login
│   ├── tienda/           tipos_cliente, categorias, productos, lista_precios, pedidos, detalle
│   ├── crm/              vendedores, clientes, prospectos, etapas, oportunidades, interacciones
│   ├── logistica/        camiones, despachos, telemetria_ruta
│   ├── bi/               endpoints agregados para el dashboard
│   ├── ia/               cliente Groq + endpoint de clasificación
│   └── Dockerfile
├── frontend/             React (tienda pública + panel interno CRM/BI)
│   └── Dockerfile        build multi-etapa → nginx
├── iot-simulator/        simulador.py, Dockerfile, docker-compose.yml
├── deploy/               docker-compose.front.yml, nginx.conf
├── docker-compose.dev.yml   postgres local + backend + frontend para desarrollar
└── .env.example
```

## Reglas de negocio clave

- **Precios por perfil**: el precio de un producto sale de `lista_precios` según `tipos_cliente` del cliente logueado. Visitante sin sesión = precios B2C.
- **Checkout**: en una transacción atómica, valida stock de cada línea (`select_for_update`), descuenta `productos.stock_disponible`, crea `pedidos` (estado Recibido, canal `web`) y `detalle_pedidos` con `precio_unitario` vigente. Si falta stock, responde 409 con el detalle.
- **B2B** debe ingresar `numero_oc`. **B2C** no.
- **Estados del pedido**: Recibido → En preparación → Despachado → Entregado | Rechazado. Pasar a Despachado exige elegir un camión (crea `despachos`). Entregado completa `despachos.fecha_entrega`.
- **Pipeline CRM**: Prospecto → Contactado → Cotización enviada → Negociación → Ganado | Perdido. Al pasar a Ganado se crea el cliente B2B y su usuario, y se guarda `prospectos.id_cliente`.
- **Alerta de frío**: `alerta_ruptura_frio = TRUE` cuando `temp_camara` está fuera de `[temp_min, temp_max]` de la categoría de la carga. Si el camión tiene un despacho activo, el rango es el más estricto entre las categorías de los productos del pedido; si no tiene, se usa el de Carnes congeladas.
- **Roles**: cliente ve solo la tienda y sus pedidos; vendedor ve CRM; despachador ve pedidos, despachos y flota; administrador ve todo, incluido el dashboard BI.

## Variables de entorno (ver `.env.example`)

`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `GROQ_API_KEY`, `GROQ_MODEL`, `DEMO_PASSWORD`, y para el simulador: `CAMION_DESDE`, `CAMION_HASTA`, `INTERVALO_SEG`, `PROB_FALLA`.

## Restricciones de AWS Academy (Learner Lab)

- Solo región **us-east-1**. Usar el rol **LabRole** / perfil **LabInstanceProfile** si un servicio pide rol IAM.
- El laboratorio se apaga al terminar la sesión: las EC2 y RDS se detienen y vuelven al iniciar. Por eso los contenedores usan `restart: unless-stopped` y Docker se habilita al arranque (`systemctl enable docker`).
- La IP pública cambia al reiniciar: la EC2 Front-Office usa **Elastic IP**.
- Presupuesto limitado: sin NAT Gateway, sin Multi-AZ, instancias pequeñas. Apagar lo que no se use.
- Las credenciales de AWS del laboratorio (si se usa AWS CLI) caducan con la sesión: nunca guardarlas en el repo.
