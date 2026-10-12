import { expect, test } from "@playwright/test";

// On a wide screen the list stays next to the open detail. It runs after the billing
// cycle, on the bill that story leaves paid.

test("the list keeps its filter while a bill opens and closes next to it", async ({ browser }) => {
  const context = await browser.newContext({
    viewport: { width: 1360, height: 850 },
    baseURL: test.info().project.use.baseURL,
    locale: "es-CO",
    timezoneId: "America/Bogota",
  });
  const page = await context.newPage();
  await page.goto("/login");
  await page.getByLabel("Correo").fill("ana.prueba@example.com");
  await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
  await page.getByRole("button", { name: "Ingresar" }).click();
  await expect(page.getByLabel("Resumen del mes")).toBeVisible();

  await page.getByRole("link", { name: "Cuentas" }).click();
  await page.getByRole("radio", { name: "Pagadas" }).click();
  await page.getByRole("link", { name: /Apto 1 · Carlos Rojas/ }).click();

  // The bill is open, and the list beside it is still the one that was filtered.
  await expect(page.getByRole("heading", { name: "Cuenta N.º 0001" })).toBeVisible();
  await expect(page.getByRole("radio", { name: "Pagadas" })).toHaveAttribute("data-state", "on");
  // One page, one main content and one heading band: the list steps back as a region.
  await expect(page.getByRole("main")).toHaveCount(1);
  await expect(page.getByRole("banner")).toHaveCount(1);

  await page.getByRole("link", { name: "Volver" }).click();
  await expect(page.getByRole("radio", { name: "Pagadas" })).toHaveAttribute("data-state", "on");
  await expect(page.getByRole("main")).toHaveCount(1);
  await context.close();
});
