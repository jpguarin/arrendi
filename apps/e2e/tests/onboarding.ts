import { expect, type Page } from "@playwright/test";

type House = {
  property: string;
  unit: string;
  tenant: string;
  email: string;
  rent: string;
};

/**
 * "Tus datos", the first thing a new owner meets: a cédula, a Bancolombia account picked
 * with taps, a signature uploaded as an image and the suggested send day.
 */
export async function fillProfile(page: Page) {
  await expect(
    page.getByRole("heading", { name: "Primero, preséntate con tus arrendatarios" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Empezar" }).click();

  await expect(page.getByRole("heading", { name: "¿Cómo te identificas?" })).toBeVisible();
  await page.getByLabel("Número de cédula").fill("52.814.337");
  await page.getByRole("button", { name: "Continuar" }).click();

  await expect(
    page.getByRole("heading", { name: "¿Cómo te pagan tus arrendatarios?" }),
  ).toBeVisible();
  await page.getByRole("radio", { name: "Bancolombia" }).click();
  await page.getByLabel("Número de cuenta").fill("123-456789-01");
  await page.getByRole("button", { name: "Continuar" }).click();

  await expect(page.getByRole("heading", { name: "Firma una sola vez" })).toBeVisible();
  await page.locator('input[type="file"]').setInputFiles("tests/fixtures/firma.png");
  await expect(page.getByRole("img", { name: "Tu firma", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Continuar" }).click();

  await expect(page.getByRole("heading", { name: "¿Qué día salen tus cuentas?" })).toBeVisible();
  await page.getByRole("button", { name: "Continuar" }).click();

  await expect(page.getByRole("heading", { name: "¿Todo bien?" })).toBeVisible();
  await page.getByRole("button", { name: "Seguir con mi inmueble" }).click();
}

/**
 * The whole onboarding, in the order the owner meets it: their data (unless the test
 * already filled it in), then the sheet with the property, its one unit and the first
 * lease, due on the 28th and started on 1 January 2026. Ends on the home screen.
 */
export async function setUpHouse(page: Page, house: House, { profileDone = false } = {}) {
  if (!profileDone) await fillProfile(page);
  await expect(page.getByRole("heading", { name: "Configura tu primer inmueble" })).toBeVisible();
  await page.getByLabel("Nombre del inmueble").fill(house.property);
  await page.getByRole("radio", { name: "Casa" }).click();
  await page.getByRole("button", { name: "Continuar" }).click();

  await page.getByRole("textbox", { name: "Unidad 1" }).fill(house.unit);
  await page.getByRole("button", { name: "Continuar" }).click();

  await page.getByLabel("Nombre del arrendatario").fill(house.tenant);
  await page.getByLabel("Correo del arrendatario").fill(house.email);
  await page.getByLabel("Canon mensual").fill(house.rent);
  await page.getByLabel("Día de pago").click();
  await page.getByRole("option", { name: "28 del mes" }).click();
  await page.getByLabel("Inicio", { exact: true }).fill("2026-01-01");
  await page.getByRole("button", { name: "Crear inmueble" }).click();

  await expect(
    page.getByRole("heading", { name: `${house.property} ya está en Arrendi` }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Ir al resumen" }).click();
  await expect(page.getByLabel("Resumen del mes")).toBeVisible();
}
