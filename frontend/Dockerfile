# Imagen del Front-Office: compila React y lo sirve con nginx (que ademas hace de proxy hacia Django).
# El contexto de build es la RAIZ del repositorio (ver deploy/docker-compose.front.yml).

# --- Etapa 1: build de React ---
FROM node:22-alpine AS build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Etapa 2: nginx ---
FROM nginx:1.27-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html
EXPOSE 80
