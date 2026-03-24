import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 3000,
    allowedHosts: ["grc.sumiriko.it"],
    proxy: {
      "/api": {
        target: "http://grc-webapp-backend-1:8000",
        changeOrigin: true,
      },
      // Django Admin + 2FA wizard: proxiati al backend, NON gestiti da React Router
      "/admin": {
        target: "http://grc-webapp-backend-1:8000",
        changeOrigin: true,
      },
      "/account": {
        target: "http://grc-webapp-backend-1:8000",
        changeOrigin: true,
      },
      // Static files del Django Admin (CSS/JS pannello)
      "/static/admin": {
        target: "http://grc-webapp-backend-1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist"
  }
});
