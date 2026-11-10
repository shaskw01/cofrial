# Plan de desarrollo — Hito 2 (entrega jueves 12-11-2026)

Cada fase termina con una **prueba concreta**. No avanzar a la siguiente sin que la prueba pase.
La columna "Rúbrica" indica qué dimensión del Hito 2 asegura cada fase.

| Fase | Cuándo | Rúbrica | Resultado |
|---|---|---|---|
| 0. Preparación | Mar 10, tarde | — | Repo, entorno local y Claude Code listos |
| 1. Backend y modelo de datos | Mar 10, tarde | 2 | 18 tablas migradas + datos semilla |
| 2. API REST | Mar 10, noche | 2 | Login, catálogo, checkout, CRM por API |
| 3. Frontend tienda + CRM | Mié 11, mañana | 2 | Flujo de compra B2B/B2C y CRM en el navegador |
| 4. Simulador IoT | Mié 11, mediodía | 3 | 5 contenedores insertando telemetría |
| 5. Dashboard BI + IA | Mié 11, tarde | 4, 5 | Panel en vivo + clasificación con Groq |
| 6. Despliegue AWS | Mié 11, noche | 1 | Todo corriendo en AWS Academy |
| 7. Pruebas y defensa | Jue 12 | 5 | Guion de demo ensayado |

> **En paralelo**: un integrante puede crear desde ya la VPC, los Security Groups y la RDS (`docs/AWS_SETUP.md`, pasos 1 a 4). La RDS tarda ~10 minutos en quedar disponible.

---

## Fase 0 — Preparación
- [ ] Instalar Git, Docker Desktop, Python 3.12, Node 20 LTS y VS Code.
- [ ] Crear la carpeta del proyecto, copiar este kit y hacer `git init`.
- [ ] Copiar `.env.example` a `.env` y completar valores locales.
- [ ] Crear cuenta gratuita en https://console.groq.com y generar `GROQ_API_KEY`.

**Prueba:** `docker --version`, `python --version`, `node --version` y `claude` responden en la terminal de VS Code.

## Fase 1 — Backend y modelo de datos
- [ ] Proyecto Django `cofrial` con las apps `cuentas`, `tienda`, `crm`, `logistica`, `bi`, `ia`.
- [ ] `settings.py` lee todo desde variables de entorno.
- [ ] Modelos exactamente como en `docs/MODELO_DATOS.md`, con `db_table` en minúsculas.
- [ ] `docker-compose.dev.yml` con `postgres:16` para desarrollo.
- [ ] Comando `python manage.py seed_demo` con los datos semilla.
- [ ] Modelos registrados en el admin de Django.

**Prueba:** `python manage.py migrate` y `seed_demo` terminan sin errores; en `/admin` se ven 50 camiones, productos con precios B2B y B2C, y pedidos históricos.

## Fase 2 — API REST (Django REST Framework)
- [ ] Autenticación: `POST /api/auth/login`, `GET /api/auth/me` (rol y tipo de cliente).
- [ ] Tienda: `GET /api/productos` (precio según perfil; filtros por categoría), `POST /api/pedidos` (checkout atómico), `GET /api/mis-pedidos`.
- [ ] CRM: CRUD de clientes y prospectos; `PATCH /api/oportunidades/{id}` (cambio de etapa; Ganado crea cliente); `POST /api/interacciones`.
- [ ] Pedidos internos: listar por estado, `PATCH` de estado, asignar camión (crea despacho), marcar entregado o rechazado.
- [ ] Permisos por rol.

**Prueba:** con un archivo `.http` o curl: login B2B → ver precio institucional → crear pedido → el stock baja → el pedido aparece para el vendedor. Pedir más stock del disponible devuelve 409.

## Fase 3 — Frontend (React)
- [ ] **Tienda pública**: catálogo con categoría y rango de temperatura, selector B2B/B2C (B2B exige login), carrito, checkout con dirección, fecha y N.º de OC (B2B), "Mis pedidos" con estado.
- [ ] **Panel interno** (`/panel`, según rol):
  - CRM: clientes, prospectos, **Kanban** del pipeline (arrastrar o botones para cambiar etapa), ficha con historial de interacciones.
  - Pedidos: tabla por estado, asignar camión, marcar entregado o rechazado.
  - Flota: últimas lecturas por camión con alerta destacada.
- [ ] Diseño basado en los wireframes del informe (Figuras 4 y 5).

**Prueba:** comprar como B2B y como B2C en el navegador; el pedido aparece en el panel del vendedor; mover una oportunidad a Ganado crea el cliente.

## Fase 4 — Simulador IoT (Docker)
- [ ] `iot-simulator/simulador.py`: simula los camiones `CAMION_DESDE`..`CAMION_HASTA`. Cada `INTERVALO_SEG` (5 s) inserta una fila por camión en `telemetria_ruta`.
- [ ] Movimiento: coordenadas que avanzan por rutas de la macrozona sur (Temuco −38,74 / −72,60 hacia Padre Las Casas, Lautaro, Villarrica, Angol, Nueva Imperial); combustible que baja y se recarga.
- [ ] Temperatura normal dentro del rango de la carga; con probabilidad `PROB_FALLA` (0,02) inicia una falla que sube la temperatura por varias lecturas y luego se recupera.
- [ ] Rango y alerta según la regla de negocio de `CLAUDE.md`.
- [ ] Reintenta la conexión si RDS no responde; logs claros.
- [ ] `docker-compose.yml` con **5 servicios** (CAM-001–010, 011–020, …), `restart: unless-stopped`.

**Prueba:** `docker compose up -d` y luego `SELECT camion_id, count(*), sum(alerta_ruptura_frio::int) FROM telemetria_ruta GROUP BY 1;` muestra los 50 camiones con datos crecientes y algunas alertas.

## Fase 5 — Dashboard BI + IA
- [ ] Endpoint `GET /api/bi/resumen` (un solo JSON):
  - Comercial: ventas de hoy y de 7 días, pedidos por canal (web/vendedor), por perfil (B2B/B2C), por estado, conversión del pipeline.
  - Operativo: alertas de la última hora, camiones en alerta ahora, temperatura promedio por camión.
  - **Cruce**: pedidos en ruta en camiones con alerta, **monto en riesgo** ($) y % de despachos con al menos una alerta.
- [ ] Página `/panel/dashboard`: tarjetas KPI + 4 gráficos (Recharts), **refresco automático cada 5 s** e indicador "Actualizado hace X s".
- [ ] IA (Groq): `POST /api/ia/clasificar` recibe el texto de un cliente y devuelve JSON `{categoria, prioridad, resumen, respuesta_sugerida}`. Categorías: reclamo_temperatura, consulta_pedido, cotizacion, reclamo_entrega, otro.
- [ ] Formulario "Ayuda / Contacto" en la tienda → clasifica con IA → crea una `interaccion` ligada al cliente → aparece en el CRM con su prioridad.
- [ ] Si Groq falla, el sistema guarda la interacción como "sin clasificar" y no se cae.

**Prueba:** con el simulador corriendo, el dashboard cambia solo; escribir "llegó la carne descongelada" se clasifica como reclamo_temperatura, prioridad alta.

## Fase 6 — Despliegue en AWS Academy
Seguir `docs/AWS_SETUP.md`.
- [ ] RDS creada y migraciones + `seed_demo` aplicados contra RDS.
- [ ] EC2 Front-Office: `docker compose -f deploy/docker-compose.front.yml up -d --build`.
- [ ] EC2 IoT: `docker compose up -d --build` en `iot-simulator/`.
- [ ] Todo con `restart: unless-stopped` y Docker habilitado al arranque.

**Prueba:** desde un celular con datos móviles, abrir `http://<Elastic IP>`, comprar y ver el pedido y el dashboard en vivo. Detener y reiniciar el lab: todo vuelve solo.

## Fase 7 — Pruebas y defensa
- [ ] Ensayar `docs/DEMO.md` completo dos veces, cronometrado.
- [ ] Capturas de respaldo de cada pantalla, por si falla la red durante la defensa.
- [ ] Repartir la defensa entre los integrantes.
