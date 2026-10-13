import { expect, test } from "@playwright/test";

// A bill is the sum of its items. A lease charges its own every month, next to the rent,
// and a manual bill charges as many as the owner adds. It runs with its own owner.

test("the items of a lease and of a manual bill, each with its amount, and their sum", async ({
  page,
}) => {
  const preview = page.getByLabel("Vista previa del documento");

  await test.step("sign in and set up a house with a lease", async () => {
    await page.goto("/login");
    await page.getByLabel("Correo").fill("diana.prueba@example.com");
    await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
    await page.getByRole("button", { name: "Ingresar" }).click();

    await page.getByLabel("Nombre del inmueble").fill("Edificio Conceptos");
    await page.getByRole("radio", { name: "Casa" }).click();
    await page.getByRole("button", { name: "Continuar" }).click();
    await page.getByRole("textbox", { name: "Unidad 1" }).fill("Apto 9");
    await page.getByRole("button", { name: "Continuar" }).click();
    await page.getByLabel("Nombre del arrendatario").fill("Laura Mora");
    await page.getByLabel("Correo del arrendatario").fill("laura.mora@example.com");
    await page.getByLabel("Canon mensual").fill("1000000");
    await page.getByLabel("Día de pago").click();
    await page.getByRole("option", { name: "28 del mes" }).click();
    await page.getByLabel("Inicio", { exact: true }).fill("2026-01-01");
    await page.getByRole("button", { name: "Crear contrato y terminar" }).click();
    await expect(page.getByLabel("Resumen del mes")).toBeVisible();
  });

  await test.step("the lease gets two items, and says what a month adds up to", async () => {
    await page.getByRole("link", { name: "Inmuebles" }).click();
    await page.getByRole("link", { name: /Apto 9 · Vivienda/ }).click();
    await page.getByRole("link", { name: /Editar contrato/ }).click();

    await page.getByRole("button", { name: "Agregar concepto" }).click();
    await page.getByLabel("Concepto", { exact: true }).fill("Administración");
    await page.getByLabel("Valor", { exact: true }).fill("200000");
    await page.getByRole("button", { name: "Agregar concepto" }).click();
    await page.getByRole("textbox", { name: "Concepto 2", exact: true }).fill("Parqueadero");
    await page.getByLabel("Valor 2").fill("80000");
    await expect(page.getByText("Total de cada mes")).toBeVisible();
    await expect(page.getByText("$1.280.000")).toBeVisible();
    await page.getByRole("button", { name: "Guardar cambios" }).click();

    await expect(page.getByRole("heading", { name: "Contrato · Apto 9" })).toBeVisible();
    const monthly = page.getByLabel("Cada mes se cobra");
    await expect(monthly).toContainText("Administración$200.000");
    await expect(monthly).toContainText("Parqueadero$80.000");
    await expect(monthly).toContainText("Total de cada mes$1.280.000");
  });

  await test.step("the bill of the month charges the rent and both items", async () => {
    await page.getByRole("button", { name: /Generar cuenta de/ }).click();
    await page.getByRole("link", { name: /N\.º 0001/ }).click();

    await expect(page.getByRole("heading", { name: "Cuenta N.º 0001" })).toBeVisible();
    await expect(preview).toContainText("Canon de arrendamiento");
    await expect(preview).toContainText("Administración$200.000");
    await expect(preview).toContainText("Parqueadero$80.000");
    await expect(preview).toContainText("Total a pagar$1.280.000");
    await expect(page.getByLabel("Saldo")).toContainText("$1.280.000");
  });

  await test.step("a manual bill adds up the items the owner gives it", async () => {
    await page.goto("/properties");
    await page.getByRole("link", { name: /Apto 9 · Vivienda/ }).click();
    await page.getByRole("link", { name: "Cobrar otro concepto" }).click();

    // It starts with one row, which cannot be removed.
    await expect(page.getByRole("button", { name: /Quitar concepto/ })).toHaveCount(0);
    await page.getByLabel("Concepto", { exact: true }).fill("Arreglo de la chapa");
    await page.getByLabel("Valor", { exact: true }).fill("80000");
    await page.getByRole("button", { name: "Agregar otro concepto" }).click();
    await page.getByRole("textbox", { name: "Concepto 2", exact: true }).fill("Pintura");
    await page.getByLabel("Valor 2").fill("45000");
    await page.getByRole("button", { name: "Agregar otro concepto" }).click();
    await page.getByRole("textbox", { name: "Concepto 3", exact: true }).fill("Sobra");
    await page.getByRole("button", { name: "Quitar concepto 3" }).click();
    await expect(page.getByRole("textbox", { name: "Concepto 3", exact: true })).toHaveCount(0);
    await expect(page.getByText("Total a pagar")).toBeVisible();
    await expect(page.getByText("$125.000")).toBeVisible();
    await page.getByLabel("Vence el").fill("2026-12-20");
    await page.getByRole("button", { name: "Generar cuenta" }).click();

    await expect(page.getByRole("heading", { name: "Cuenta N.º 0002" })).toBeVisible();
    await expect(preview).toContainText("Arreglo de la chapa");
    await expect(preview).toContainText("Pintura$45.000");
    await expect(preview).toContainText("Total a pagar$125.000");
    // One due date for the whole bill.
    await expect(preview.getByText(/Vence el/)).toHaveCount(1);
  });

  await test.step("an empty row does not go through", async () => {
    await page.goto("/properties");
    await page.getByRole("link", { name: /Apto 9 · Vivienda/ }).click();
    await page.getByRole("link", { name: "Cobrar otro concepto" }).click();
    await page.getByLabel("Vence el").fill("2026-12-20");
    await page.getByRole("button", { name: "Generar cuenta" }).click();

    await expect(page.getByText("Escribe el concepto.")).toBeVisible();
    await expect(page.getByText("Escribe el valor.")).toBeVisible();
  });
});
