/// <reference types="vitest/config" />

import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "ROBOARC_");
  return {
    plugins: [react()],
    test: {
      include: ["src/**/*.test.ts"],
    },
    server: {
      proxy: {
        "/api": {
          target: env.ROBOARC_API_TARGET || "http://127.0.0.1:8000",
          changeOrigin: true,
          ws: true,
        },
      },
    },
  };
});
