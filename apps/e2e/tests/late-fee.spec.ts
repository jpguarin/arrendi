import { expect, test } from "@playwright/test";

import { setUpHouse } from "./onboarding";

// A lease may charge a late fee: a percentage of the rent, once, on the bill of the next
// month. The bill says so from the start. Which bill charges it, and letting a fee go,
// depend on the date, so they are tested in the API, where the day is set.

/** Today's day of the month in Colombia. */
function dayInBogota(): number {
  return Number(
    new Intl.DateTimeFormat("en-CA", { timeZone: "America/Bogota", day: "numeric" }).format(
      new Date(),
    ),
  );
}

test("the late fee: set on the lease and announced on the bill", async ({ page }) => {
  const preview = page.getByLabel("Vista previa del documento");

  await test.step("sign in and set up a house with a lease due on the 28th", async () => {
    await page.goto("/login");
    await page.getByLabel("Correo").fill("fiona.prueba@example.com");
    await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
    await page.getByRole("button", { name: "Ingresar" }).click();

    await setUpHouse(page, {
      property: "Casa Mora",
      unit: "Apto 7",
      tenant: "Iván Soto",
      email: "ivan.soto@example.com",
      rent: "1000000",
    });
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
  });

  await test.step("what is typed with the late fee off does not stop the form or the fee", async () => {
    await page.getByLabel("Días de gracia").fill("45");
    await page.getByRole("switch", { name: /Cobrar recargo por mora/ }).click();
    await page.getByRole("button", { name: "Guardar cambios" }).click();

    await expect(page.getByRole("heading", { name: "Contrato · Apto 7" })).toBeVisible();
    await expect(page.getByText("No se cobra")).toBeVisible();
    // Turned back on, the percentage it had is still there.
    await page.getByRole("link", { name: /Editar contrato/ }).click();
    await page.getByRole("switch", { name: /Cobrar recargo por mora/ }).click();
    await expect(page.getByLabel("Porcentaje del canon")).toHaveValue("2,5");
    await expect(page.getByLabel("Días de gracia")).toHaveValue("0");
    await page.getByRole("button", { name: "Guardar cambios" }).click();
    await expect(page.getByText("2,5 % del canon")).toBeVisible();
  });

  // After the 28th the bill of the month is issued past its deadline, and has no late fee.
  test.skip(dayInBogota() > 28, "after the 28th the bill is issued too late to have a fee");

  await test.step("the bill of the month says what paying late costs", async () => {
    await page.getByRole("button", { name: /Generar cuenta de/ }).click();
    await page.getByRole("link", { name: /N\.º 0001/ }).click();

    await expect(page.getByRole("heading", { name: "Cuenta N.º 0001" })).toBeVisible();
    await expect(preview).toContainText(
      "la siguiente cuenta incluirá un recargo por mora de $25.000.",
    );
    // The fee is not on this bill.
    await expect(preview).toContainText("Total a pagar$1.000.000");
  });
});
