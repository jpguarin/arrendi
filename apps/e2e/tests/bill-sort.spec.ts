import { expect, type Page, test } from "@playwright/test";

import { setUpHouse } from "./onboarding";

// On a wide screen the headings Vence and Estado order the list of bills: up, down, and
// back to the months.

/** A manual bill on the one unit of the house, due on `due`. */
async function manualBill(page: Page, concept: string, due: string) {
  await page.goto("/properties");
  await page.getByRole("link", { name: /Apto 3 · Vivienda/ }).click();
  await page.getByRole("link", { name: "Cobrar otro concepto" }).click();
  await page.getByLabel("Concepto", { exact: true }).fill(concept);
  await page.getByLabel("Valor", { exact: true }).fill("50000");
  await page.getByLabel("Vence el").fill(due);
  await page.getByRole("button", { name: "Generar cuenta" }).click();
  await expect(page.getByRole("heading", { name: /Cuenta N\.º/ })).toBeVisible();
}

test("the headings Vence and Estado order the bills, and a third click goes back to the months", async ({
  browser,
}) => {
  const context = await browser.newContext({
    viewport: { width: 1360, height: 850 },
    baseURL: test.info().project.use.baseURL,
    locale: "es-CO",
    timezoneId: "America/Bogota",
  });
  const page = await context.newPage();
  // The numbers of the bills, top to bottom.
  const order = () => page.getByRole("listitem").getByText(/^N\.º \d{4}$/).allTextContents();

  await test.step("sign in and issue three bills: one overdue, two due later", async () => {
    await page.goto("/login");
    await page.getByLabel("Correo").fill("gina.prueba@example.com");
    await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
    await page.getByRole("button", { name: "Ingresar" }).click();
    await setUpHouse(page, {
      property: "Casa Orden",
      unit: "Apto 3",
      tenant: "Julia Paz",
      email: "julia.paz@example.com",
      rent: "900000",
    });

    await manualBill(page, "Pintura", "2030-12-20");
    await manualBill(page, "Arreglo de la chapa", "2026-01-10");
    await manualBill(page, "Cambio de grifo", "2030-06-20");
  });

  await test.step("by default, by month", async () => {
    await page.goto("/bills");
    await expect(page.getByRole("heading", { name: "Diciembre 2030" })).toBeVisible();
    await expect.poll(order).toEqual(["N.º 0001", "N.º 0003", "N.º 0002"]);
  });

  const due = page.getByRole("button", { name: /^Ordenar por vencimiento/ });
  const status = page.getByRole("button", { name: /^Ordenar por estado/ });

  await test.step("Vence: the oldest first, then the latest first", async () => {
    await due.click();
    await expect(due).toHaveAccessibleName(/de la más antigua a la más reciente/);
    // One list: no months.
    await expect(page.getByRole("heading", { name: "Diciembre 2030" })).toHaveCount(0);
    await expect.poll(order).toEqual(["N.º 0002", "N.º 0003", "N.º 0001"]);

    await due.click();
    await expect(due).toHaveAccessibleName(/de la más reciente a la más antigua/);
    await expect.poll(order).toEqual(["N.º 0001", "N.º 0003", "N.º 0002"]);
  });

  await test.step("Estado: the overdue first, the rest by due date", async () => {
    await status.click();
    await expect(status).toHaveAccessibleName(/de la más urgente a la menos urgente/);
    await expect(due).toHaveAccessibleName(/sin ordenar/);
    await expect.poll(order).toEqual(["N.º 0002", "N.º 0003", "N.º 0001"]);
  });

  await test.step("a third click on the same heading goes back to the months", async () => {
    await status.click();
    await status.click();
    await expect(status).toHaveAccessibleName(/sin ordenar/);
    await expect(page.getByRole("heading", { name: "Diciembre 2030" })).toBeVisible();
    await expect.poll(order).toEqual(["N.º 0001", "N.º 0003", "N.º 0002"]);
  });

  await context.close();
});
