# Guion de la defensa en vivo (8 a 10 minutos)

Cada paso muestra una dimensión de la rúbrica del Hito 2. Tener abiertas estas pestañas antes de empezar: consola AWS (EC2 y RDS), tienda, panel CRM, dashboard y una terminal SSH a la EC2 IoT.

| # | Qué mostrar | Rúbrica | Quién |
|---|---|---|---|
| 1 | **Consola AWS**: las 2 EC2 en `running`, la RDS `Available` y sin acceso público, los 3 Security Groups. Explicar en 30 s la Figura 1. | 1 | |
| 2 | **Tienda como B2C** (sin sesión): catálogo con rangos de temperatura y precio público. Agregar 2 productos al carrito. | 2 | |
| 3 | **Login B2B** (Hospital Regional): el mismo producto ahora muestra el precio institucional. Checkout con N.º de OC → pedido creado. Mostrar que el stock bajó. | 2 | |
| 4 | **CRM como vendedor**: el pedido recién creado aparece en Recibido. Kanban: mover una oportunidad de Negociación a **Ganado** → se crea el cliente. | 2 | |
| 5 | **Despacho**: pasar el pedido a En preparación y luego a Despachado asignando un camión. | 2 | |
| 6 | **IoT**: en la terminal de la EC2 IoT, `docker compose ps` (5 contenedores) y `logs -f` con inserciones en vivo. Explicar los 6 campos exigidos. | 3 | |
| 7 | **Dashboard BI**: KPI comerciales + alertas de frío actualizándose solas. Señalar el **cruce**: monto en riesgo por camiones con alerta. | 4 | |
| 8 | **IA**: desde la tienda, escribir "el pedido llegó con la carne blanda y caliente". Mostrar la clasificación (reclamo_temperatura, alta) y cómo aparece en el CRM. | 5 | |
| 9 | Cierre: cómo cada pantalla elimina un dolor del diagnóstico (teléfono, Excel, WhatsApp). | 5 | |

## Preguntas probables del profesor
- ¿Por qué la RDS no tiene acceso público y cómo se conecta el simulador? (SG-RDS referencia SG-IoT.)
- ¿Qué pasa si se cae la EC2 IoT? (La tienda sigue funcionando: nodos separados.)
- ¿Cómo se calcula `alerta_ruptura_frio`? (Rango de la categoría de la carga.)
- ¿Por qué Docker y no ECS? (Trade-off 2 del Módulo 3.)
- ¿Qué pasa si se acaba la cuota gratuita de la IA? (La interacción se guarda como "sin clasificar".)
- ¿Dónde están las credenciales? (`.env` fuera del repositorio.)
