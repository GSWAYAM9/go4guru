import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 0,
  use: {
    baseURL: process.env.E2E_WEB_URL || "http://127.0.0.1:3000",
    headless: true,
    screenshot: "only-on-failure",
  },
});
