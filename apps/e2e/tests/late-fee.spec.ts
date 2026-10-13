import { expect, test } from "@playwright/test";

// A lease may charge a late fee: a percentage of the rent, once, on the bill of the next
// month. The bill says so from the start, and the owner may let a fee go. Which bill
// charges it depends on the date, so that part is tested in the API, where the day is set.

/** Today's day of the month in Colombia. */
function dayInBogota(): number {
  return Number(
    new Intl.DateTimeFormat("en-CA", { timeZone: "America/Bogota", day: "numeric" }).format(
      new Date(),
    ),
  );
}

test("the late fee: set on the lease, announced on the bill, waived and brought back", async ({
  page,
}) => {
  const preview = page.getByLabel("Vista previa del documento");
  const lateFee = page.getByLabel("Recargo por mora");

  await test.step("sign in and set up a house with a lease due on the 1st", async () => {
    await page.goto("/login");
    await page.getByLabel("Correo").fill("fiona.prueba@example.com");
    await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
    await page.getByRole("button", { name: "Ingresar" }).click();

    await page.getByLabel("Nombre del inmueble").fill("Casa Mora");
    await page.getByRole("radio", { name: "Casa" }).click();
    await page.getByRole("button", { name: "Continuar" }).click();
    await page.getByRole("textbox", { name: "Unidad 1" }).fill("Apto 7");
    await page.getByRole("button", { name: "Continuar" }).click();
    await page.getByLabel("Nombre del arrendatario").fill("Iván Soto");
    await page.getByLabel("Correo del arrendatario").fill("ivan.soto@example.com");
    await page.getByLabel("Canon mensual").fill("1000000");
    await page.getByLabel("Día de pago").click();
    await page.getByRole("option", { name: "1 del mes", exact: true }).click();
    await page.getByLabel("Inicio", { exact: true }).fill("2026-01-01");
    await page.getByRole("button", { name: "Crear contrato y terminar" }).click();
    await expect(page.getByLabel("Resumen del mes")).toBeVisible();
  });

  await test.step("the lease gets a late fee of 2,5 %", async () => {
    await page.getByRole("link", { name: "Inmuebles" }).click();
    await page.getByRole("link", { name: /Apto 7 · Vivienda/ }).click();
    await expect(page.getByText("No se cobra")).toBeVisible();
    await page.getByRole("link", { name: /Editar contrato/ }).click();

    // Nothing to fill in until it is turned on.
    await expect(page.getByLabel("Porcentaje del canon")).toHaveCount(0);
    await page.getByRole("switch", { name: /Cobrar recargo por mora/ }).click();
    await expect(page.getByRole("switch", { name: /Cobrar recargo por mora/ })).toBeChecked();
    await page.getByLabel("Porcentaje del canon").fill("2,5");
    await expect(page.getByText("Con este canon, el recargo es de $25.000.")).toBeVisible();
    await expect(page.getByLabel("Días de gracia")).toHaveValue("0");
    await page.getByRole("button", { name: "Guardar cambios" }).click();

    await expect(page.getByRole("heading", { name: "Contrato · Apto 7" })).toBeVisible();
    await expect(page.getByText("2,5 % del canon")).toBeVisible();
  });

  await test.step("a percentage that is not one does not go through", async () => {
    await page.getByRole("link", { name: /Editar contrato/ }).click();
    await page.getByLabel("Porcentaje del canon").fill("150");
    await page.getByRole("button", { name: "Guardar cambios" }).click();
    await expect(page.getByText(/Escribe un porcentaje mayor que 0/)).toBeVisible();
    await page.goBack();
  });

  await test.step("the bill of the month says what paying late costs", async () => {
    await page.getByRole("button", { name: /Generar cuenta de/ }).click();
    await page.getByRole("link", { name: /N\.º 0001/ }).click();

    await expect(page.getByRole("heading", { name: "Cuenta N.º 0001" })).toBeVisible();
    await expect(preview).toContainText("la siguiente cuenta incluirá un recargo por mora de $25.000.");
    // The fee is not on this bill.
    await expect(preview).toContainText("Total a pagar$1.000.000");
  });

  // The bill was due on the 1st with no days of grace: it is late on any other day.
  test.skip(dayInBogota() === 1, "on the 1st the bill is still in time");

  await test.step("the owner lets the fee go, and brings it back", async () => {
    await expect(lateFee).toContainText("La próxima cuenta del mes de este contrato cobrará $25.000");
    await page.getByRole("button", { name: "No cobrar este recargo" }).click();
    await page.getByRole("button", { name: "No cobrarlo" }).click();

    await expect(lateFee).toContainText("Decidiste no cobrar el recargo de $25.000");
    await page.getByRole("button", { name: "Volver a cobrarlo" }).click();
    await expect(page.getByRole("button", { name: "No cobrar este recargo" })).toBeVisible();
  });
});
