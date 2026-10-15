import { expect, type Page } from "@playwright/test";

type House = {
  property: string;
  unit: string;
  tenant: string;
  email: string;
  rent: string;
};

/**
 * The onboarding sheet, filled in the order the owner meets it: the property, its one
 * unit and the first lease, due on the 28th and started on 1 January 2026. Ends on the
 * home screen.
 */
export async function setUpHouse(page: Page, house: House) {
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

  await expect(page.getByRole("heading", { name: `${house.property} ya está en Arrendi` })).toBeVisible();
  await page.getByRole("button", { name: "Ir al resumen" }).click();
  await expect(page.getByLabel("Resumen del mes")).toBeVisible();
}
