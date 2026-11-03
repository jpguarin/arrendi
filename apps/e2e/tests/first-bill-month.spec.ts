import { expect, test } from "@playwright/test";

import { firstOfMonth, setUpHouse } from "./onboarding";

// A lease registered after it started: its first bill is of the month it started, and the
// next one is of the current month. It runs with its own owner.

const MONTHS = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
];

function monthName(isoDate: string): string {
  const [year, month] = isoDate.split("-").map(Number);
  return `${MONTHS[month - 1]} ${year}`;
}

test("the first bill of a lease that already started is of its first month", async ({ page }) => {
  const started = monthName(firstOfMonth(1));
  const current = monthName(firstOfMonth());
  const generate = (month: string) =>
    page.getByRole("button", { name: `Generar cuenta de ${month.toLowerCase()}` });

  await test.step("sign in and set up a lease that started last month", async () => {
    await page.goto("/login");
    await page.getByLabel("Correo").fill("elena.prueba@example.com");
    await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
    await page.getByRole("button", { name: "Ingresar" }).click();

    await setUpHouse(
      page,
      {
        property: "Casa Atrasada",
        unit: "Apto 9",
        tenant: "Rosa Díaz",
        email: "rosa.diaz@example.com",
        rent: "800000",
      },
      { startDate: firstOfMonth(1) },
    );
    await page.getByRole("link", { name: "Inmuebles" }).click();
    await page.getByRole("link", { name: /Apto 9 · Vivienda/ }).click();
  });

  await test.step("the first bill is of the month it started", async () => {
    await generate(started).click();
    await page.getByRole("link", { name: /N\.º 0001/ }).click();

    await expect(page.getByRole("heading", { name: "Cuenta N.º 0001" })).toBeVisible();
    await expect(page.getByLabel("Vista previa del documento")).toContainText(started);
    await page.goBack();
  });

  await test.step("the next one is of the current month, and then there are no more", async () => {
    await generate(current).click();
    await expect(page.getByRole("link", { name: /N\.º 0002/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /Generar cuenta de/ })).toHaveCount(0);
  });
});
