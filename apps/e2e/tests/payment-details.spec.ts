import { expect, test } from "@playwright/test";

import { setUpHouse } from "./onboarding";

// How to pay: what Ajustes says, unless the lease has its own, unless the bill has its
// own. It runs with its own owner, apart from the billing cycle.

const DEFAULT = "Bancolombia ahorros 123";
const OF_THE_LEASE = "Daviplata 300 111 2233";
const OF_THE_BILL = "En efectivo, al plomero";

test("payment details: from Ajustes, from the lease and from the bill itself", async ({ page }) => {
  const preview = page.getByLabel("Vista previa del documento");
  let firstBill = "";

  await test.step("sign in and set up a house with a lease", async () => {
    await page.goto("/login");
    await page.getByLabel("Correo").fill("beto.prueba@example.com");
    await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
    await page.getByRole("button", { name: "Ingresar" }).click();

    await setUpHouse(page, {
      property: "Casa Pagos",
      unit: "Local 1",
      tenant: "Marta Díaz",
      email: "marta.diaz@example.com",
      rent: "800000",
    });
  });

  await test.step("Ajustes holds the default", async () => {
    await page.getByRole("link", { name: "Ajustes" }).click();
    await page.getByLabel("Cómo te pagan").fill(DEFAULT);
    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(page.getByRole("button", { name: "Guardar" })).toBeEnabled();
  });

  await test.step("a bill of a lease without its own takes the default", async () => {
    await page.getByRole("link", { name: "Inmuebles" }).click();
    await page.getByRole("link", { name: /Local 1 · Vivienda/ }).click();
    await expect(page.getByRole("heading", { name: "Contrato · Local 1" })).toBeVisible();
    await page.getByRole("link", { name: "Cobrar otro concepto" }).click();
    await page.getByLabel("Concepto").fill("Arreglo de la chapa");
    await page.getByLabel("Valor").fill("80000");
    await page.getByLabel("Vence el").fill("2026-12-20");
    await page.getByRole("button", { name: "Generar cuenta" }).click();

    await expect(page.getByRole("heading", { name: "Cuenta N.º 0001" })).toBeVisible();
    await expect(preview).toContainText(`Pagar a: ${DEFAULT}`);
    firstBill = page.url();
  });

  await test.step("the lease gets its own, and its bills carry them", async () => {
    await page.goto("/properties");
    await page.getByRole("link", { name: /Local 1 · Vivienda/ }).click();
    await page.getByRole("link", { name: /Editar contrato/ }).click();
    await page.getByLabel("Cómo te pagan (opcional)").fill(OF_THE_LEASE);
    await page.getByRole("button", { name: "Guardar cambios" }).click();

    await expect(page.getByRole("heading", { name: "Contrato · Local 1" })).toBeVisible();
    await expect(page.getByLabel("Datos de pago de este contrato")).toContainText(OF_THE_LEASE);
    await page.getByRole("button", { name: /Generar cuenta de/ }).click();
    await page.getByRole("link", { name: /N\.º 0002/ }).click();
    await expect(preview).toContainText(`Pagar a: ${OF_THE_LEASE}`);
  });

  await test.step("a bill with its own carries those, and only that bill", async () => {
    await page.goto("/properties");
    await page.getByRole("link", { name: /Local 1 · Vivienda/ }).click();
    await page.getByRole("link", { name: "Cobrar otro concepto" }).click();
    await page.getByLabel("Concepto").fill("Destape de la tubería");
    await page.getByLabel("Valor").fill("120000");
    await page.getByLabel("Vence el").fill("2026-12-20");
    await page.getByLabel("Cómo te pagan (opcional)").fill(OF_THE_BILL);
    await page.getByRole("button", { name: "Generar cuenta" }).click();

    await expect(page.getByRole("heading", { name: "Cuenta N.º 0003" })).toBeVisible();
    await expect(preview).toContainText(`Pagar a: ${OF_THE_BILL}`);
  });

  await test.step("the first bill still says what it was issued with", async () => {
    await page.goto(firstBill);
    await expect(page.getByRole("heading", { name: "Cuenta N.º 0001" })).toBeVisible();
    await expect(preview).toContainText(`Pagar a: ${DEFAULT}`);
  });
});
