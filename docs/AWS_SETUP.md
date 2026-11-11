# Despliegue en AWS Academy (Learner Lab) — paso a paso

Todo en la región **us-east-1**. Los nombres y rangos son los del Informe Hito 1 (Tabla de subredes y Security Groups). Hacerlo desde la consola web de AWS.

## 1. VPC y subredes
1. VPC → **Create VPC** → "VPC only": nombre `vpc-cofrial`, IPv4 CIDR `10.0.0.0/16`.
2. Subnets → Create subnet en `vpc-cofrial`:
   - `subred-publica` — us-east-1a — `10.0.1.0/24`
   - `subred-privada-a` — us-east-1a — `10.0.3.0/24`
   - `subred-privada-b` — us-east-1b — `10.0.4.0/24`
3. En `subred-publica`: Actions → Edit subnet settings → activar **Auto-assign public IPv4**.
4. Internet gateways → Create `igw-cofrial` → Attach to VPC `vpc-cofrial`.
5. Route tables → Create `rt-publica` (vpc-cofrial) → Routes: agregar `0.0.0.0/0` → `igw-cofrial` → Subnet associations: `subred-publica`.
   (Las privadas quedan con la tabla principal, que solo tiene la ruta local.)

## 2. Security Groups (en vpc-cofrial)
AWS no permite nombres que empiecen con `sg-`, por eso llevan el prefijo `cofrial-`.
| Nombre | Entrada |
|---|---|
| `cofrial-sg-web` | HTTP 80 desde 0.0.0.0/0 · HTTPS 443 desde 0.0.0.0/0 · SSH 22 desde **My IP** |
| `cofrial-sg-iot` | SSH 22 desde **My IP** (nada más) |
| `cofrial-sg-rds` | PostgreSQL 5432 desde **cofrial-sg-web** · PostgreSQL 5432 desde **cofrial-sg-iot** |

## 3. DB Subnet Group
RDS → Subnet groups → Create: `dbsg-cofrial`, VPC `vpc-cofrial`, zonas us-east-1a y us-east-1b, subredes `10.0.3.0/24` y `10.0.4.0/24`.

## 4. Base de datos RDS
RDS → Create database → Standard create:
- Engine **PostgreSQL**, versión **16.x** (la más reciente 16 disponible).
- Template **Free tier** o Dev/Test · Single-AZ.
- Identificador `cofrial-db` · usuario `cofrial_admin` · contraseña segura (guardarla en `.env`, no en git).
- Clase **db.t3.micro** · almacenamiento **gp3 20 GB**, sin autoscaling.
- Conectividad: VPC `vpc-cofrial`, subnet group `dbsg-cofrial`, **Public access: No**, Security group `cofrial-sg-rds` (quitar el default).
- Additional configuration: Initial database name `cofrial`, backups automáticos **7 días**.
- Esperar estado **Available** (~10 min) y copiar el **Endpoint** → `DB_HOST`.

## 5. EC2 Front-Office
EC2 → Launch instance:
- Nombre `ec2-front-office` · AMI **Amazon Linux 2023** · tipo **t3.small**.
- Key pair: usar `vockey` (descargar `labsuser.pem` desde "AWS Details" del Learner Lab) o crear uno nuevo.
- Network: `vpc-cofrial`, `subred-publica`, Security group `cofrial-sg-web`.
- Storage: 20 GB gp3.
- Advanced → User data:
```bash
#!/bin/bash
dnf update -y
dnf install -y docker git
systemctl enable --now docker
usermod -aG docker ec2-user
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
# buildx: Compose lo exige para construir imagenes y el paquete docker de Amazon Linux 2023 no lo trae
curl -SL https://github.com/docker/buildx/releases/download/v0.21.2/buildx-v0.21.2.linux-amd64 -o /usr/local/lib/docker/cli-plugins/docker-buildx
chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
```
- Elastic IPs → Allocate → Associate a `ec2-front-office`.

## 6. EC2 Back-Office IoT
Igual que el paso 5, pero: nombre `ec2-iot`, tipo **t3.micro**, Security group **`cofrial-sg-iot`**, sin Elastic IP.

## 7. Subir el código y levantar
Desde la terminal de VS Code (PowerShell), con `labsuser.pem` en una carpeta segura:
```powershell
ssh -i C:\ruta\labsuser.pem ec2-user@<IP_EC2>
```
En cada EC2:
```bash
git clone <URL del repositorio> cofrial && cd cofrial
nano .env        # pegar los valores de producción (ver la lista de abajo)
```
Valores del `.env` de producción (el mismo archivo en las dos EC2, en la raíz del repositorio):
```
DJANGO_SECRET_KEY=<clave nueva, larga y aleatoria>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<Elastic IP>
CORS_ALLOWED_ORIGINS=http://<Elastic IP>
DB_HOST=<endpoint de RDS>
DB_PORT=5432
DB_NAME=cofrial
DB_USER=cofrial_admin
DB_PASSWORD=<contraseña de RDS>
GROQ_API_KEY=<clave de console.groq.com>
GROQ_MODEL=openai/gpt-oss-20b
DEMO_PASSWORD=<contraseña de las cuentas demo>
INTERVALO_SEG=5
PROB_FALLA=0.02
```
- Front-Office: `docker compose -f deploy/docker-compose.front.yml up -d --build`. El backend aplica las
  migraciones solo al arrancar. La primera vez, cargar los datos demo:
  `docker compose -f deploy/docker-compose.front.yml exec backend python manage.py seed_demo`.
- IoT: `cd iot-simulator && docker compose up -d --build` (lee el `.env` de la raíz). Levantarlo **después**
  del Front-Office, porque necesita las tablas y los camiones ya creados.
- Para actualizar el código más adelante: `git pull` y repetir el `up -d --build` en cada EC2.

Si el repositorio es privado, usar un token de GitHub de solo lectura, o copiar con `scp`.

## 8. Verificación
- `http://<Elastic IP>` abre la tienda.
- En la EC2 IoT: `docker compose ps` muestra 5 contenedores `Up` y `docker compose logs -f --tail 20` muestra inserciones.
- El dashboard cambia solo cada 5 segundos.
- Al detener y volver a iniciar el lab, todo vuelve sin intervención.

## Para la defensa
Iniciar el Learner Lab **20 minutos antes**: las instancias y la RDS tardan en arrancar.
