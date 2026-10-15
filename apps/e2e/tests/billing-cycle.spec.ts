import { expect, test } from "@playwright/test";

// The whole cycle, as the owner lives it: sign in, set up the house, issue the bill of
// the month, take a partial payment and then the rest.

const RENT = "$1.000.000";

/** Today's day of the month in Colombia, which decides whether the bill is born overdue. */
function dayInBogota(): number {
  return Number(
    new Intl.DateTimeFormat("en-CA", { timeZone: "America/Bogota", day: "numeric" }).format(
      new Date(),
    ),
  );
}

test("onboarding, a bill, a partial payment and the rest", async ({ page }) => {
  // The lease is due on the 28th: after that day the bill of the month is already overdue,
  // and a partial payment leaves it overdue instead of partial.
  const afterPartial = dayInBogota() > 28 ? "Vencida" : "Parcial";

  await test.step("sign in", async () => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login$/);
    await page.getByLabel("Correo").fill("ana.prueba@example.com");
    await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
    await page.getByRole("button", { name: "Ingresar" }).click();
  });

  await test.step("onboarding: the property, confirmed part by part", async () => {
    await expect(page.getByRole("heading", { name: "Configura tu primer inmueble" })).toBeVisible();
    await expect(page.getByText("Hola, Ana")).toBeVisible();
    await page.getByLabel("Nombre del inmueble").fill("Casa Prueba");
    await page.getByRole("radio", { name: "Casa" }).click();
    await page.getByRole("button", { name: "Continuar" }).click();
    // The part folds into what it holds, with a way back in.
    await expect(page.getByRole("link", { name: /Casa Prueba · Casa.*Editar/ })).toBeVisible();
  });

  await test.step("a reload keeps what was typed", async () => {
    await page.getByRole("textbox", { name: "Unidad 1" }).fill("Apto 1");
    await page.reload();
    await expect(page.getByRole("textbox", { name: "Unidad 1" })).toHaveValue("Apto 1");
    await page.getByRole("button", { name: "Continuar" }).click();
  });

  await test.step("onboarding: the first lease, and creating it all", async () => {
    // On a phone the summary is the strip at the bottom, with the button that creates it.
    const summary = page.getByRole("contentinfo");
    await expect(summary).toContainText("Casa Prueba");
    await expect(summary).toContainText("1 unidad · 1 contrato");
    await page.getByLabel("Nombre del arrendatario").fill("Carlos Rojas");
    await page.getByLabel("Correo del arrendatario").fill("carlos.rojas@example.com");
    await page.getByLabel("Canon mensual").fill("1000000");
    await page.getByLabel("Día de pago").click();
    await page.getByRole("option", { name: "28 del mes" }).click();
    await page.getByLabel("Inicio", { exact: true }).fill("2026-01-01");
    await page.getByRole("button", { name: "Crear inmueble" }).click();

    await expect(page.getByRole("heading", { name: "Casa Prueba ya está en Arrendi" })).toBeVisible();
    await expect(page.getByText("1 unidad y el contrato de Carlos Rojas")).toBeVisible();
    await page.getByRole("button", { name: "Ir al resumen" }).click();
  });

  await test.step("the home screen starts empty", async () => {
    await expect(page.getByText("Aún no hay cuentas este mes")).toBeVisible();
    await expect(page.getByText("de $0 esperados")).toBeVisible();
  });

  await test.step("issue the bill of the month from the lease", async () => {
    await page.getByRole("link", { name: "Inmuebles" }).click();
    await page.getByRole("link", { name: /Apto 1 · Vivienda/ }).click();
    await expect(page.getByRole("heading", { name: "Contrato · Apto 1" })).toBeVisible();
    await page.getByRole("button", { name: /Generar cuenta de/ }).click();
    await page.getByRole("link", { name: /N\.º 0001/ }).click();

    await expect(page.getByRole("heading", { name: "Cuenta N.º 0001" })).toBeVisible();
    await expect(page.getByLabel("Vista previa del documento")).toContainText(RENT);
    await expect(page.getByLabel("Vista previa del documento")).toContainText("Carlos Rojas");
  });

  await test.step("a partial payment leaves a balance", async () => {
    await page.getByRole("link", { name: "Registrar pago" }).click();
    await expect(page.getByRole("heading", { name: "Registrar pago" })).toBeVisible();
    // It comes filled in with the whole balance.
    await expect(page.getByLabel("Valor recibido")).toHaveValue(RENT);
    await page.getByLabel("Valor recibido").fill("400000");
    await page.getByRole("radio", { name: "Nequi" }).click();
    // No email provider in this run; the receipt has its own tests in the API.
    await page.getByRole("switch").click();
    await page.getByRole("button", { name: "Guardar pago" }).click();

    await expect(page.getByRole("heading", { name: "Cuenta N.º 0001" })).toBeVisible();
    await expect(page.getByRole("banner").getByText(afterPartial)).toBeVisible();
    await expect(page.getByText("Saldo $600.000")).toBeVisible();
    await expect(page.getByText(/· Nequi$/)).toBeVisible();
  });

  await test.step("the home screen shows what came in and what is left", async () => {
    await page.goto("/");
    await expect(page.getByText("Recaudado este mes")).toBeVisible();
    const summary = page.getByLabel("Resumen del mes");
    await expect(summary).toContainText("$400.000");
    await expect(summary).toContainText(`de ${RENT} esperados`);
    await expect(summary).toContainText("$600.000");
    await expect(page.getByRole("heading", { name: "Por cobrar" })).toBeVisible();
    await expect(page.getByText("Apto 1 · Carlos Rojas")).toBeVisible();
  });

  await test.step("the rest, from the home screen in two taps", async () => {
    await page.getByRole("link", { name: "Registrar pago" }).click();
    await expect(page.getByLabel("Valor recibido")).toHaveValue("$600.000");
    await page.getByRole("button", { name: "Guardar pago" }).click();

    // Back on the home screen, with the month collected in full.
    await expect(page.getByRole("heading", { name: "Pagadas" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Por cobrar" })).toHaveCount(0);
    const summary = page.getByLabel("Resumen del mes");
    await expect(summary).toContainText(RENT);
    await expect(summary).toContainText("0 de 1 unidad");
  });

  await test.step("the bill is paid, in its detail and in the list", async () => {
    await page.getByRole("link", { name: "Cuentas" }).click();
    await expect(page.getByText(`${RENT} de ${RENT}`)).toBeVisible();
    await page.getByRole("link", { name: /Apto 1 · Carlos Rojas/ }).click();
    await expect(page.getByRole("banner").getByText("Pagada")).toBeVisible();
    await expect(page.getByText("Sin saldo")).toBeVisible();
    await expect(page.getByRole("link", { name: "Registrar pago" })).toHaveCount(0);
  });
});
