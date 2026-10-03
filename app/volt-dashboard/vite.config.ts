import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import { inspectAttr } from 'plugin-inspect-react-code'

// https://vite.dev/config/
export default defineConfig({
  base: '/',
  plugins: [inspectAttr(), react()],
  server: {
    port: 3000,
    host: true,
    allowedHosts: true,
    proxy: {
      '/api': process.env.OMNI_API_TARGET || 'http://127.0.0.1:8500',
      '/webhook': process.env.OMNI_API_TARGET || 'http://127.0.0.1:8500',
      '/process': process.env.OMNI_API_TARGET || 'http://127.0.0.1:8500',
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
