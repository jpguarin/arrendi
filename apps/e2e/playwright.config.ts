import { defineConfig, devices } from "@playwright/test";

import { API_PORT, API_URL, SUPABASE_URL, WEB_PORT, WEB_URL } from "./ports.ts";

// Everything runs on this computer: the web, the API against a local PostgreSQL, and a
// stand-in for Supabase's Auth and Storage. See docs/arquitectura.md.
const database =
  process.env.E2E_API_DATABASE_URL ??
  "postgresql://arrendi_api:arrendi_test@localhost:5432/arrendi_e2e";

export default defineConfig({
  testDir: "./tests",
  globalSetup: "./global-setup.ts",
  // One story told in order, on one database.
  workers: 1,
  fullyParallel: false,
  retries: 0,
  timeout: 90_000,
  reporter: [["list"]],
  use: {
    baseURL: WEB_URL,
    // Arrendi is used on a phone first.
    ...devices["Pixel 7"],
    locale: "es-CO",
    timezoneId: "America/Bogota",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "node fakes/supabase.ts",
      url: `${SUPABASE_URL}/health`,
      reuseExistingServer: false,
    },
    {
      command: `.venv/bin/uvicorn app.main:app --port ${API_PORT}`,
      cwd: "../api",
      url: `${API_URL}/api/health`,
      reuseExistingServer: false,
      env: {
        ENVIRONMENT: "local",
        DATABASE_URL: database,
        SUPABASE_URL,
        SUPABASE_SECRET_KEY: "e2e-secret",
        STORAGE_BUCKET: "arrendi",
        // No email provider: the API refuses to send, and nothing leaves this computer.
        EMAIL_API_KEY: "",
        EMAIL_SENDER: "",
        EMAIL_TEST_INBOX: "",
        CRON_SECRET: "",
      },
    },
    {
      command: `pnpm exec next dev --port ${WEB_PORT}`,
      cwd: "../web",
      url: `${WEB_URL}/login`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        NEXT_PUBLIC_SUPABASE_URL: SUPABASE_URL,
        NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: "e2e-publishable",
        API_URL,
        // Its own build folder, so it does not collide with a `pnpm dev` that is open.
        NEXT_DIST_DIR: ".next-e2e",
      },
    },
  ],
});
