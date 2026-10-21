import { expect, test } from "@playwright/test";

// An address that leads nowhere shows "Aquí no vive nadie", with the address and a way
// back. Whoever is signed out signs in first.

test("an address that does not exist: sign in first, then the empty house", async ({ page }) => {
  await test.step("signed out, the proxy asks to sign in", async () => {
    await page.goto("/cuentas");
    await expect(page).toHaveURL(/\/login$/);
  });

  await test.step("signed in, the page says so and shows the address", async () => {
    await page.getByLabel("Correo").fill("nora.prueba@example.com");
    await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
    await page.getByRole("button", { name: "Ingresar" }).click();
    await expect(page).not.toHaveURL(/\/login$/);

    const response = await page.goto("/cuentas");
    expect(response?.status()).toBe(404);
    await expect(page).toHaveTitle(/Página no encontrada/);
    await expect(page.getByRole("heading", { level: 1, name: "Aquí no vive nadie" })).toBeVisible();
    await expect(page.getByText("/cuentas", { exact: true })).toBeVisible();
  });

  await test.step("on a phone, a long address does not scroll the page sideways", async () => {
    await page.setViewportSize({ width: 390, height: 844 });
    const address = "/bils/4fde6292-1f15-4942-b6e0-13a0c69ae1b2/payment";
    await page.goto(address);
    await expect(page.getByText(address, { exact: true })).toBeAttached();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBe(0);
  });

  await test.step("Volver goes back, and Ir al resumen goes home", async () => {
    await page.getByRole("link", { name: "Ir al resumen" }).click();
    await expect(page).not.toHaveURL(/\/cuentas$/);

    await page.goto("/cuentas");
    await page.getByRole("button", { name: "Volver" }).click();
    await expect(page).not.toHaveURL(/\/cuentas$/);
  });
});
