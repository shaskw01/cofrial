# Cofrial SpA — Prototipo Hito 2

E-commerce B2B/B2C + CRM + simulación IoT de cadena de frío + dashboard BI, desplegado en AWS Academy.
Detalles del diseño en `CLAUDE.md` y `docs/`.

## Puesta en marcha local (Windows)

Requisitos: Git, Docker Desktop (abierto), Python 3.12–3.14, Node 20+.

```powershell
git clone https://github.com/shaskw01/cofrial.git
cd cofrial
copy .env.example .env          # completar DJANGO_SECRET_KEY, DB_PASSWORD y DEMO_PASSWORD
                                # si ya usas el puerto 5432, pon DB_PORT=5433

docker compose -f docker-compose.dev.yml up -d db     # Postgres 16 local

cd backend
py -3.14 -m venv .venv          # o la versión 3.12/3.13 que tengas
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo      # datos demo (idempotente; --reset-historial para regenerar pedidos y CRM)
python manage.py runserver      # http://localhost:8000/admin  →  admin@cofrial.cl / DEMO_PASSWORD
```

## Trabajo en equipo con git

- `main` siempre debe funcionar. Cada cambio va en una rama: `git switch -c fase2-api-tienda`.
- Antes de empezar el día: `git switch main && git pull`, y luego `git switch tu-rama && git merge main`.
- Sube tu rama (`git push -u origin tu-rama`) y abre un Pull Request en GitHub; otro integrante lo revisa y lo une.
- **Migraciones**: solo una persona a la vez modifica `models.py`. Si dos ramas crean migraciones en la
  misma app, al unirlas hay que correr `python manage.py makemigrations --merge`.
- Nunca subas `.env` ni archivos `.pem` (ya están en `.gitignore`). Cada integrante tiene su propio `.env`.
