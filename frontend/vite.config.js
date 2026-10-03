import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    server: {
        port: 3000,
        proxy: {
            '/api/visual_scan': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, '')
            },
            '/auth': {
                target: 'http://localhost:8000',
                changeOrigin: true
            }
        }
    }
})
