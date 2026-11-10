import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// En desarrollo, /api se redirige al backend local (BACKEND_PORT del .env de la raiz).
// En AWS lo mismo lo hace nginx, asi el frontend siempre llama a rutas relativas.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '..', '')
  const backend = env.VITE_BACKEND_URL || `http://localhost:${env.BACKEND_PORT || 8000}`
  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5174,
      strictPort: true,
      proxy: { '/api': { target: backend, changeOrigin: true } },
    },
  }
})
