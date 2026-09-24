import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/invoice': 'http://localhost:8000'   // local dev only
    }
  }
})
