import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Tailwind v4 is a Vite plugin, not a PostCSS step - there is no tailwind.config.js
// on purpose. The /api proxy lets the frontend call the backend on the same
// origin, so no CORS preflight in dev and no base URL to change at build time.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
