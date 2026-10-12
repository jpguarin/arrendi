import { expect, test } from "@playwright/test";

// On a wide screen the list stays next to the open detail. It runs after the billing
// cycle, on the bill that story leaves paid.

test("the list keeps its filter and follows the changes of the bill open next to it", async ({ browser }) => {
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

  // A change made in the detail reaches the list beside it without leaving the screen:
  // with a payment removed the bill is no longer paid, so the filter drops it.
  await page.getByRole("link", { name: /Apto 1 · Carlos Rojas/ }).click();
  await page.getByRole("button", { name: "Eliminar el pago de $600.000" }).click();
  await page.getByRole("button", { name: "Eliminar pago" }).click();
  await expect(page.getByText("Saldo $600.000")).toBeVisible();
  const list = page.getByRole("region", { name: "Lista" });
  await expect(list.getByText("No hay cuentas con estos filtros.")).toBeVisible();
  await list.getByRole("radio", { name: "Por cobrar" }).click();
  await expect(list.getByRole("link", { name: /Apto 1 · Carlos Rojas/ })).toBeVisible();
  await context.close();
});
