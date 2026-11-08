import { defineConfig, devices } from "@playwright/test";

// e2e-тесты сценариев из docs/scenarios.md; бэкенд ожидается с CMDB_AUTH_DISABLED=true
export default defineConfig({
  testDir: "./e2e",
  use: { baseURL: "http://localhost:5173", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: true,
  },
});
