import { expect, test, type Page } from "@playwright/test";

// Подготовка к С2 (docs/scenarios.md): editor попадает в оболочку приложения и видит список CI.
// Keycloak и бэкенд не нужны: сессия подкладывается в sessionStorage, сеть заглушена.
const AUTHORITY = "https://sso.test/realms/cmdb";
const CLIENT_ID = "cmdb-ui";

async function stubNetwork(page: Page) {
  await page.route(`${AUTHORITY}/**`, (route) => route.fulfill({ status: 404, body: "" }));
  await page.route("**/api/**", (route) => route.fulfill({ json: [] }));
}

async function loginAs(page: Page, username: string) {
  const user = {
    access_token: "test-token",
    token_type: "Bearer",
    scope: "openid profile",
    profile: { sub: username, preferred_username: username },
    // Далеко в будущем, чтобы oidc-client-ts не пытался обновлять токен
    expires_at: Math.floor(Date.now() / 1000) + 24 * 3600,
  };
  await page.addInitScript(
    ([key, value]) => sessionStorage.setItem(key, value),
    [`oidc.user:${AUTHORITY}:${CLIENT_ID}`, JSON.stringify(user)],
  );
}

test("без сессии показывается кнопка входа через SSO", async ({ page }) => {
  await stubNetwork(page);
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Войти через SSO" })).toBeVisible();
});

test("editor видит оболочку и список CI", async ({ page }) => {
  await stubNetwork(page);
  await loginAs(page, "editor");
  await page.goto("/");

  await expect(page).toHaveURL(/\/cis$/);
  await expect(page.getByRole("heading", { name: "CMDB" })).toBeVisible();
  await expect(page.getByText("editor")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Конфигурационные единицы" })).toBeVisible();
});
