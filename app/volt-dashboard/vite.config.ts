import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import { inspectAttr } from 'plugin-inspect-react-code'

const apiTarget = process.env.API_PROXY_TARGET || 'http://127.0.0.1:8500'

// https://vite.dev/config/
export default defineConfig({
  base: '/',
  plugins: [inspectAttr(), react()],
  server: {
    host: true,
    port: 3000,
    proxy: {
      '/api': apiTarget,
      '/webhook': apiTarget,
      '/process': apiTarget,
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
