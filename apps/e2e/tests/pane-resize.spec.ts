import { expect, type Page, test } from "@playwright/test";

import { setUpHouse } from "./onboarding";

// From tablet up, the owner drags the edge of the detail panel to make it wider or
// narrower. The width stays in this browser and is the same in Inmuebles and Cuentas.
// It runs with its own owner.

const OWNER = "pablo.prueba@example.com";

async function signIn(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Correo").fill(OWNER);
  await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
  await page.getByRole("button", { name: "Ingresar" }).click();
}

test("the detail panel: dragged wider, remembered, moved with keys and put back", async ({
  browser,
  page: phone,
}) => {
  const context = await browser.newContext({
    viewport: { width: 1360, height: 850 },
    baseURL: test.info().project.use.baseURL,
    locale: "es-CO",
    timezoneId: "America/Bogota",
  });
  const page = await context.newPage();
  const edge = page.getByRole("separator", { name: "Ancho del panel" });

  await test.step("sign in, set up a house and open its lease", async () => {
    await signIn(page);
    await setUpHouse(page, {
      property: "Casa Ancha",
      unit: "Apto 1",
      tenant: "Sara Gil",
      email: "sara.gil@example.com",
      rent: "750000",
    });
    await page.getByRole("link", { name: "Inmuebles" }).click();
    await page.getByRole("link", { name: /Apto 1 · Vivienda/ }).click();
    await expect(page.getByRole("heading", { name: "Contrato · Apto 1" })).toBeVisible();
    // The width of the design on a desktop.
    await expect(edge).toHaveAttribute("aria-valuenow", "408");
  });

  await test.step("dragging the edge to the left widens the panel", async () => {
    const box = (await edge.boundingBox())!;
    const y = box.y + box.height / 2;
    await page.mouse.move(box.x + box.width / 2, y);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width / 2 - 200, y, { steps: 10 });
    await page.mouse.up();

    await expect(edge).toHaveAttribute("aria-valuenow", "608");
  });

  await test.step("the width stays after reloading, and Cuentas uses it too", async () => {
    await page.reload();
    await expect(edge).toHaveAttribute("aria-valuenow", "608");

    await page.getByRole("button", { name: /Generar cuenta de/ }).click();
    await page.getByRole("link", { name: "Cuentas", exact: true }).click();
    await page.getByRole("link", { name: /Apto 1 · Sara Gil/ }).click();
    await expect(page.getByRole("heading", { name: "Cuenta N.º 0001" })).toBeVisible();
    await expect(edge).toHaveAttribute("aria-valuenow", "608");
  });

  await test.step("the keys move it, never past the limits", async () => {
    await edge.focus();
    await page.keyboard.press("End");
    // The panel stops at 720 px.
    await expect(edge).toHaveAttribute("aria-valuenow", "720");
    await page.keyboard.press("ArrowLeft");
    await expect(edge).toHaveAttribute("aria-valuenow", "720");
    await page.keyboard.press("ArrowRight");
    await expect(edge).toHaveAttribute("aria-valuenow", "704");
    await page.keyboard.press("Home");
    await expect(edge).toHaveAttribute("aria-valuenow", "360");
  });

  await test.step("a double click puts back the width of the design, for good", async () => {
    await edge.dblclick();
    await expect(edge).toHaveAttribute("aria-valuenow", "408");
    await page.reload();
    await expect(edge).toHaveAttribute("aria-valuenow", "408");
  });

  await context.close();

  await test.step("on a phone the detail takes the screen and has no edge", async () => {
    await signIn(phone);
    await expect(phone.getByLabel("Resumen del mes")).toBeVisible();
    await phone.goto("/properties");
    await phone.getByRole("link", { name: /Apto 1 · Vivienda/ }).click();
    await expect(phone.getByRole("heading", { name: "Contrato · Apto 1" })).toBeVisible();
    await expect(phone.getByRole("separator", { name: "Ancho del panel" })).toBeHidden();
  });
});
