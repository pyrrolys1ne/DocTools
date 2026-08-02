import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // 开发时把 API 请求转发到本地 FastAPI 后端（含 WebSocket）
      "/api": { target: "http://127.0.0.1:8000", ws: true },
    },
  },
});
