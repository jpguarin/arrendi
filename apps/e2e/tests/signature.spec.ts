import { expect, test } from "@playwright/test";

import { setUpHouse } from "./onboarding";

// The owner's signature closes every bill. It is uploaded or drawn in Ajustes, and a bill
// keeps the one it was issued with. It runs with its own owner.

test("the signature: uploaded, on the bill, drawn and taken away", async ({ page }) => {
  const preview = page.getByLabel("Vista previa del documento");
  const signature = page.getByRole("img", { name: "Tu firma" });
  let signedBill = "";

  await test.step("sign in and set up a house with a lease", async () => {
    await page.goto("/login");
    await page.getByLabel("Correo").fill("eva.prueba@example.com");
    await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
    await page.getByRole("button", { name: "Ingresar" }).click();

    await setUpHouse(page, {
      property: "Casa Firma",
      unit: "Apto 3",
      tenant: "Hugo Paz",
      email: "hugo.paz@example.com",
      rent: "700000",
    });
  });

  await test.step("the signature of the onboarding is taken away in Ajustes", async () => {
    await page.goto("/settings");
    await expect(signature).toBeVisible();
    await page.getByRole("button", { name: "Quitar firma" }).click();
    await expect(signature).toHaveCount(0);
  });

  await test.step("a bill issued without a signature leaves a line to sign", async () => {
    await page.getByRole("link", { name: "Inmuebles" }).click();
    await page.getByRole("link", { name: /Apto 3 · Vivienda/ }).click();
    await page.getByRole("link", { name: "Cobrar otro concepto" }).click();
    await page.getByLabel("Concepto", { exact: true }).fill("Arreglo de la chapa");
    await page.getByLabel("Valor", { exact: true }).fill("80000");
    await page.getByLabel("Vence el").fill("2026-12-20");
    await page.getByRole("button", { name: "Generar cuenta" }).click();

    await expect(page.getByRole("heading", { name: "Cuenta N.º 0001" })).toBeVisible();
    await expect(preview).not.toContainText("Firmada");
  });

  await test.step("the owner uploads a signature in Ajustes and sees it", async () => {
    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: "Firma" })).toBeVisible();
    await expect(signature).toHaveCount(0);
    await page.locator('input[type="file"]').setInputFiles("tests/fixtures/firma.png");

    await expect(signature).toBeVisible();
    await expect(page.getByRole("button", { name: "Quitar firma" })).toBeVisible();
  });

  await test.step("the bill of the month is issued signed", async () => {
    await page.goto("/properties");
    await page.getByRole("link", { name: /Apto 3 · Vivienda/ }).click();
    await page.getByRole("button", { name: /Generar cuenta de/ }).click();
    await page.getByRole("link", { name: /N\.º 0002/ }).click();

    await expect(page.getByRole("heading", { name: "Cuenta N.º 0002" })).toBeVisible();
    await expect(preview).toContainText("Firmada");
    signedBill = page.url();
  });

  await test.step("a signature drawn with the finger replaces it", async () => {
    await page.goto("/settings");
    await expect(signature).toBeVisible();
    const before = await signature.getAttribute("src");
    await page.getByRole("button", { name: "Dibujar firma" }).click();
    const sheet = page.getByRole("img", { name: "Hoja para dibujar tu firma" });
    // Nothing to use until something is drawn.
    await expect(page.getByRole("button", { name: "Usar firma" })).toBeDisabled();
    const box = (await sheet.boundingBox())!;
    await page.mouse.move(box.x + 40, box.y + 120);
    await page.mouse.down();
    await page.mouse.move(box.x + 110, box.y + 40, { steps: 6 });
    await page.mouse.move(box.x + 170, box.y + 130, { steps: 6 });
    await page.mouse.move(box.x + 260, box.y + 70, { steps: 6 });
    await page.mouse.up();
    await page.getByRole("button", { name: "Usar firma" }).click();

    await expect(sheet).toHaveCount(0);
    await expect(signature).toBeVisible();
    await expect(signature).not.toHaveAttribute("src", before!);
  });

  await test.step("taking it away leaves the bills already issued as they were", async () => {
    await page.getByRole("button", { name: "Quitar firma" }).click();
    await expect(signature).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Quitar firma" })).toHaveCount(0);

    await page.goto(signedBill);
    await expect(page.getByRole("heading", { name: "Cuenta N.º 0002" })).toBeVisible();
    await expect(preview).toContainText("Firmada");
  });
});
