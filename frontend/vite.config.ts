import { fileURLToPath, URL } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

const BACKEND = process.env.VITE_BACKEND_URL ?? 'http://127.0.0.1:8787'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    // Im Dev-Betrieb spricht das Frontend denselben relativen /api-Pfad an
    // wie im Kiosk-Build, in dem FastAPI das dist/ selbst ausliefert.
    proxy: {
      '/api': { target: BACKEND, changeOrigin: false },
    },
  },
})
