/// <reference types="vitest/config" />

import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "ROBOARC_");
  const proxy = {
    "/api": {
      target: env.ROBOARC_API_TARGET || "http://127.0.0.1:8000",
      changeOrigin: true,
      ws: true,
    },
    "/artifacts": {
      target: env.ROBOARC_ARTIFACT_TARGET || "http://127.0.0.1:8080",
      changeOrigin: true,
      rewrite: (path: string) => path.replace(/^\/artifacts/, ""),
    },
  };
  return {
    base: process.env.ROBOARC_REVIEW_BASE ?? "/",
    plugins: [react()],
    test: {
      include: ["src/**/*.test.ts"],
    },
    server: {
      proxy,
    },
    preview: { proxy },
  };
});
