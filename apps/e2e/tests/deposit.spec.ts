import { expect, test } from "@playwright/test";

// The deposit of a lease is charged once: as its own item, next to the rent, on the first
// bill of the month. It runs with its own owner, apart from the billing cycle.

test("the first bill of the month charges the deposit as its own item", async ({ page }) => {
  const preview = page.getByLabel("Vista previa del documento");

  await test.step("sign in and set up a house with a lease", async () => {
    await page.goto("/login");
    await page.getByLabel("Correo").fill("carla.prueba@example.com");
    await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
    await page.getByRole("button", { name: "Ingresar" }).click();

    await page.getByLabel("Nombre del inmueble").fill("Casa Depósito");
    await page.getByRole("radio", { name: "Casa" }).click();
    await page.getByRole("button", { name: "Continuar" }).click();
    await page.getByRole("textbox", { name: "Unidad 1" }).fill("Apto 5");
    await page.getByRole("button", { name: "Continuar" }).click();
    await page.getByLabel("Nombre del arrendatario").fill("Pedro Ruiz");
    await page.getByLabel("Correo del arrendatario").fill("pedro.ruiz@example.com");
    await page.getByLabel("Canon mensual").fill("900000");
    await page.getByLabel("Día de pago").click();
    await page.getByRole("option", { name: "28 del mes" }).click();
    await page.getByLabel("Inicio", { exact: true }).fill("2026-01-01");
    await page.getByRole("button", { name: "Crear contrato y terminar" }).click();
    await expect(page.getByLabel("Resumen del mes")).toBeVisible();
  });

  await test.step("the lease gets a deposit, to be charged", async () => {
    await page.getByRole("link", { name: "Inmuebles" }).click();
    await page.getByRole("link", { name: /Apto 5 · Vivienda/ }).click();
    await page.getByRole("link", { name: /Editar contrato/ }).click();
    // Nothing to choose until there is a deposit.
    const charge = page.getByRole("switch", { name: /Cobrar el depósito en la primera cuenta/ });
    await expect(charge).toHaveCount(0);
    await page.getByLabel("Depósito (opcional)").fill("500000");
    await expect(charge).toBeChecked();
    await page.getByRole("button", { name: "Guardar cambios" }).click();
    await expect(page.getByRole("heading", { name: "Contrato · Apto 5" })).toBeVisible();
  });

  await test.step("the bill of the month has both items and adds them up", async () => {
    await page.getByRole("button", { name: /Generar cuenta de/ }).click();
    await page.getByRole("link", { name: /N\.º 0001/ }).click();

    await expect(page.getByRole("heading", { name: "Cuenta N.º 0001" })).toBeVisible();
    await expect(preview).toContainText("Canon de arrendamiento");
    await expect(preview).toContainText("$900.000");
    await expect(preview).toContainText("Depósito");
    await expect(preview).toContainText("$500.000");
    await expect(preview).toContainText("Total a pagar$1.400.000");
    await expect(page.getByLabel("Saldo")).toContainText("$1.400.000");
  });

  await test.step("with the first bill out, the lease has nothing left to choose", async () => {
    await page.goto("/properties");
    await page.getByRole("link", { name: /Apto 5 · Vivienda/ }).click();
    await page.getByRole("link", { name: /Editar contrato/ }).click();
    await expect(page.getByLabel("Depósito (opcional)")).toHaveValue("$500.000");
    await expect(page.getByRole("switch", { name: /Cobrar el depósito/ })).toHaveCount(0);
  });
});
