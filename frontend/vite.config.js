import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      '/api/v1': 'http://localhost:8100',
      '/api': 'http://localhost:8100',
      '/health': 'http://localhost:8100',
    },
  },
})
