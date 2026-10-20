import { expect, test } from "@playwright/test";

import { setUpHouse } from "./onboarding";

// The inventory of the unit: an optional file of the lease, next to the signed lease.
// It goes up with a new lease or later from its screen, and is opened and replaced there.
// It runs with its own owner.

test("the inventory: with a new lease, opened and replaced", async ({ page }) => {
  const inventory = page.getByRole("region", { name: "Inventario" });

  await test.step("sign in, set up a house and add a vacant unit", async () => {
    await page.goto("/login");
    await page.getByLabel("Correo").fill("olga.prueba@example.com");
    await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
    await page.getByRole("button", { name: "Ingresar" }).click();

    await setUpHouse(page, {
      property: "Casa Inventario",
      unit: "Apto 1",
      tenant: "Lucía Mora",
      email: "lucia.mora@example.com",
      rent: "900000",
    });

    await page.getByRole("link", { name: "Inmuebles" }).click();
    await page.getByRole("link", { name: "Agregar unidad a Casa Inventario" }).click();
    await page.getByLabel("Nombre de la unidad").fill("Apto 2");
    await page.getByRole("button", { name: "Agregar unidad" }).click();
  });

  await test.step("the new lease goes up with its inventory", async () => {
    await page.getByRole("link", { name: /Apto 2 · Vivienda/ }).click();
    await page.getByLabel("Nombre del arrendatario").fill("Raúl Vega");
    await page.getByLabel("Correo del arrendatario").fill("raul.vega@example.com");
    await page.getByLabel("Canon mensual").fill("850000");
    await page.getByLabel("Día de pago").click();
    await page.getByRole("option", { name: "5 del mes", exact: true }).click();
    await page.getByLabel("Inicio", { exact: true }).fill("2026-10-01");
    // The second picker of the form; the first one is for the signed lease.
    await page.locator('input[type="file"]').nth(1).setInputFiles("tests/fixtures/inventario.pdf");
    await expect(page.getByRole("button", { name: "Quitar inventario.pdf" })).toBeVisible();
    await page.getByRole("button", { name: "Crear contrato" }).click();

    await expect(page.getByRole("heading", { name: "Contrato · Apto 2" })).toBeVisible();
    await expect(inventory).toContainText("inventario.pdf");
    await expect(inventory).toContainText("Subido el");
    // The signed lease was not picked, so it is still waiting for its file.
    await expect(page.getByRole("button", { name: "Subir contrato firmado" })).toBeVisible();
  });

  await test.step("the owner opens the inventory", async () => {
    // Headless Chromium downloads a PDF instead of showing it, so the tab says little:
    // the temporary link the API hands out is what to check.
    const link = page.waitForResponse((response) =>
      /\/api\/leases\/[^/]+\/inventory$/.test(response.url()),
    );
    const opened = page.waitForEvent("popup");
    await inventory.getByRole("button", { name: "Ver" }).click();
    const answer = await (await link).json();
    expect(answer.name).toBe("inventario.pdf");
    expect(answer.url).toMatch(/\/inventories\/.+\/inventario\.pdf/);
    await (await opened).close();
  });

  await test.step("a photo replaces it", async () => {
    await inventory.locator('input[type="file"]').setInputFiles("tests/fixtures/firma.png");

    await expect(inventory).toContainText("firma.png");
    await expect(inventory).not.toContainText("inventario.pdf");
  });
});
