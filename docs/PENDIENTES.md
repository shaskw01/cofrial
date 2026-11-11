# Pendientes antes de la defensa (jueves 12-11-2026)

Revisión hecha el martes 10-11-2026 sobre la rama `fase5-bi-ia`, contra la rúbrica del Hito 2 y `docs/PLAN.md`.
Marcar cada punto al terminarlo.

## Estado por dimensión de la rúbrica

| # | Dimensión | Estado | Qué falta |
|---|---|---|---|
| 1 | Despliegue en AWS Academy | Desplegado | Falta la prueba del punto 6 (celular y reinicio del lab). |
| 2 | E-commerce y CRM operativo | Listo en local | Probarlo ya desplegado. |
| 3 | Simulación IoT con Docker en EC2 | Listo en local | Correrlo en la EC2 IoT dedicada, contra RDS. |
| 4 | Dashboard BI en vivo | Listo en local | Probarlo ya desplegado, con el simulador de la EC2. |
| 5 | IA costo cero + defensa | Casi listo | Probar la IA por la interfaz (punto 7) y ensayar la demo (punto 9). |

## Bloqueantes para desplegar

- [x] **1. Crear los archivos de despliegue** (hecho en la rama `fase6-despliegue` y probado en local con
  `DJANGO_DEBUG=False`: tienda, API, admin con estilos, dashboard e IA):
  - `frontend/Dockerfile`: build multi-etapa de React y nginx.
  - `deploy/nginx.conf`: sirve el frontend, redirige `/api` y `/admin` a Django y sirve los archivos estáticos del admin.
  - `deploy/docker-compose.front.yml`: servicios `nginx` y `backend` (gunicorn), con `restart: unless-stopped`.
  - Estáticos del admin: el backend corre `collectstatic` al arrancar y nginx los sirve desde un volumen compartido.
- [x] **2. Subir el código a GitHub** (hecho el 10-11: fases 2 a 6 unidas a `main` y subidas): `main` en GitHub solo tiene la Fase 1. Las fases 2 a 5 están en ramas
  locales (`fase2-api`, `fase3-frontend`, `fase4-iot`, `fase5-bi-ia`, `fase6-despliegue`; cada una contiene a la
  anterior, así que basta unir la última).
  Hay que unirlas a `main` y hacer push, porque las EC2 clonan desde GitHub.
- [x] **3. Infraestructura AWS** (hecho el 10-11: VPC, SG, RDS `cofrial-db`, EC2 `ec2-front-office` (Elastic IP 34.197.29.147) y `ec2-iot`) (`docs/AWS_SETUP.md`, pasos 1 a 6): VPC y subredes, los 3 Security Groups,
  DB Subnet Group, RDS PostgreSQL 16, EC2 Front-Office con Elastic IP y EC2 IoT.
- [x] **4. `.env` de producción en cada EC2** (hecho el 10-11 en las dos EC2) (nunca en git; la plantilla completa está en `docs/AWS_SETUP.md`, paso 7):
  - `DJANGO_DEBUG=False`
  - `DJANGO_SECRET_KEY` nueva, larga y aleatoria
  - `DJANGO_ALLOWED_HOSTS` con la Elastic IP
  - `CORS_ALLOWED_ORIGINS` con `http://<Elastic IP>`
  - `DB_HOST` con el endpoint de RDS, `DB_PORT=5432`, y la contraseña de RDS en `DB_PASSWORD`
  - `GROQ_API_KEY` y `GROQ_MODEL=openai/gpt-oss-20b`
  - `DEMO_PASSWORD`
- [x] **5. Levantar y cargar datos** (hecho el 10-11: Front-Office arriba, `seed_demo` en RDS, 5 simuladores insertando): en Front-Office, `docker compose -f deploy/docker-compose.front.yml up -d --build`,
  luego `seed_demo` contra RDS (las migraciones se aplican solas al arrancar). En la EC2 IoT, `cd iot-simulator && docker compose up -d --build`
  (lee el `.env` de la raíz del repositorio).
- [ ] **6. Prueba de la Fase 6**: desde un celular con datos móviles abrir `http://<Elastic IP>`, comprar, y ver
  el pedido y el dashboard en vivo. Detener y reiniciar el lab: todo debe volver solo.

## Pendientes en el entorno local

- [x] **7. Reiniciar el backend local** (hecho el 10-11: la IA clasifica por la interfaz) para que tome `GROQ_API_KEY` (el `.env` se lee solo al arrancar):
  `Ctrl+C` y `python manage.py runserver 8001`. Después probar por la interfaz: como `cliente@gmail.com`,
  en **Ayuda**, escribir "llegó la carne descongelada"; debe quedar como reclamo por temperatura, prioridad
  alta, y aparecer en **Requerimientos** para el vendedor. La clasificación ya se probó contra Groq real
  desde el backend, pero no por el formulario.
- [ ] **8. Confirmar dos decisiones** que se tomaron sin estar definidas en el informe:
  - Un pedido rechazado **no** devuelve el stock.
  - Si un camión lleva carga congelada y refrigerada a la vez, la alerta usa el rango de la categoría más fría.

## Defensa (Fase 7)

- [ ] **9. Ensayar `docs/DEMO.md` completo dos veces**, cronometrado (8 a 10 minutos).
- [ ] **10. Repartir la defensa** entre los tres integrantes: la columna "Quién" de `docs/DEMO.md` está vacía.
- [ ] **11. Capturas de respaldo** de cada pantalla, por si falla la red durante la defensa.
- [ ] **12. Dejar pedidos despachados antes de la demo**: el "monto en riesgo" del dashboard solo sube cuando
  un pedido en ruta viaja en un camión con alerta. Con pocos pedidos en ruta puede mostrar $0.
- [ ] **13. Iniciar el Learner Lab 20 minutos antes**: las instancias y la RDS tardan en arrancar.

## Mejoras opcionales (no afectan la rúbrica)

- [ ] Contrastar el diseño con los wireframes del informe (Figuras 4 y 5); no están en el repositorio.
- [ ] Mapa de camiones con Leaflet (el plan lo marca como opcional). Hoy la flota muestra las coordenadas en texto.
- [ ] Ajustar `PROB_FALLA` si se quieren menos camiones en alerta a la vez (con 0.02 hay entre 5 y 10 de 50).
- [ ] Limpiar los datos de prueba de la base local (pedidos 37 y 38, cliente "Clínica QA" y dos mensajes de
  ayuda). No afectan a AWS: la RDS parte con datos semilla limpios.

## Ya verificado (no hay que rehacerlo)

- Las 18 tablas del modelo de datos existen tal cual, sin migraciones pendientes.
- `telemetria_ruta` tiene los 6 campos exigidos, con sus nombres y tipos.
- 23 pruebas automáticas del backend pasan (`python manage.py test`) y el frontend compila.
- Flujo completo por la interfaz: compra B2B con orden de compra, el pedido aparece al vendedor, crear
  prospecto, pasar a Ganado (crea el cliente B2B y puede ingresar), preparación, despacho con camión y entrega.
- Simulador: 5 contenedores insertando solos, con reconexión automática si la base se cae.
- Dashboard: datos en vivo de la base, refresco cada 5 segundos y cruce de ventas con alertas de frío.
- No hay contraseñas ni claves en el repositorio; los `.env` están ignorados por git.
