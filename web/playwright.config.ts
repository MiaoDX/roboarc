import { defineConfig, devices } from "@playwright/test";

const reuseExistingServer = process.env.CI !== "true";
const apiPort = process.env.ROBOARC_API_PORT ?? "8000";
const apiOrigin = `http://127.0.0.1:${apiPort}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 7_000 },
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: `python -m uvicorn roboarc.api:app --host 127.0.0.1 --port ${apiPort}`,
      cwd: "..",
      url: `${apiOrigin}/api/v1/health`,
      reuseExistingServer,
      timeout: 30_000,
    },
    {
      command: `ROBOARC_API_TARGET=${apiOrigin} npm run dev -- --host 127.0.0.1 --port 5173`,
      url: "http://127.0.0.1:5173",
      reuseExistingServer,
      timeout: 30_000,
    },
  ],
});
