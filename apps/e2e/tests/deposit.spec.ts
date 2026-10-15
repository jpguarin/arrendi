import { expect, test } from "@playwright/test";

import { setUpHouse } from "./onboarding";

// The deposit of a lease is charged once: as its own item, next to the rent, on the first
// bill of the month. It runs with its own owner, apart from the billing cycle.

test("the first bill of the month charges the deposit as its own item", async ({ page }) => {
  const preview = page.getByLabel("Vista previa del documento");

  await test.step("sign in and set up a house with a lease", async () => {
    await page.goto("/login");
    await page.getByLabel("Correo").fill("carla.prueba@example.com");
    await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
    await page.getByRole("button", { name: "Ingresar" }).click();

    await setUpHouse(page, {
      property: "Casa Depósito",
      unit: "Apto 5",
      tenant: "Pedro Ruiz",
      email: "pedro.ruiz@example.com",
      rent: "900000",
    });
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
