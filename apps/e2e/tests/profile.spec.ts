import { expect, test } from "@playwright/test";

// "Tus datos": before the first property, a new owner answers four questions whose
// answers go on every bill. It runs with its own owner.

test("the owner's data: four questions, a review and then the property", async ({ page }) => {
  const continueButton = page.getByRole("button", { name: "Continuar" });
  const PAYMENT = "Nequi al 3001234567\nA nombre de Pilar Prueba, NIT 900.123.456-7";

  await test.step("a new owner starts with their data", async () => {
    await page.goto("/login");
    await page.getByLabel("Correo").fill("pilar.prueba@example.com");
    await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
    await page.getByRole("button", { name: "Ingresar" }).click();

    await expect(
      page.getByRole("heading", { name: "Primero, preséntate con tus arrendatarios" }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Empezar" }).click();
  });

  await test.step("who charges: the name comes filled in, the document is asked", async () => {
    await expect(page.getByLabel("Tu nombre o razón social")).not.toHaveValue("");
    await page.getByLabel("Tu nombre o razón social").fill("Pilar Prueba");
    await continueButton.click();
    await expect(page.getByText("Escribe el número de tu documento.")).toBeVisible();

    await page.getByRole("radio", { name: "NIT" }).click();
    await page.getByLabel("Número de NIT").fill("900.123.456-7");
    await continueButton.click();
  });

  await test.step("how they get paid: a tap on the wallet and the text writes itself", async () => {
    await expect(
      page.getByRole("heading", { name: "¿Cómo te pagan tus arrendatarios?" }),
    ).toBeVisible();
    await continueButton.click();
    await expect(page.getByText("Elige dónde te consignan.")).toBeVisible();

    await page.getByRole("radio", { name: "Nequi" }).click();
    // A wallet goes by the phone: there is no kind of account to pick.
    await expect(page.getByRole("radio", { name: "Ahorros" })).toHaveCount(0);
    await page.getByLabel("Celular").fill("3001234567");
    const written = page.getByText("Así lo leerá tu arrendatario").locator("..");
    await expect(written).toContainText("Nequi al 3001234567");
    await expect(written).toContainText("A nombre de Pilar Prueba, NIT 900.123.456-7");
    await continueButton.click();
  });

  await test.step("the signature: required, and drawn with the finger", async () => {
    await expect(page.getByRole("heading", { name: "Firma una sola vez" })).toBeVisible();
    await continueButton.click();
    await expect(
      page.getByText("Dibuja tu firma o sube una foto de ella para seguir."),
    ).toBeVisible();

    await page.getByRole("button", { name: "Dibujar firma" }).click();
    const sheet = page.getByRole("img", { name: "Hoja para dibujar tu firma" });
    const box = (await sheet.boundingBox())!;
    await page.mouse.move(box.x + 40, box.y + 120);
    await page.mouse.down();
    await page.mouse.move(box.x + 120, box.y + 40, { steps: 6 });
    await page.mouse.move(box.x + 220, box.y + 110, { steps: 6 });
    await page.mouse.up();
    await page.getByRole("button", { name: "Usar firma" }).click();
    await expect(page.getByRole("img", { name: "Tu firma", exact: true })).toBeVisible();
    await continueButton.click();
  });

  await test.step("the send day: the 1st is suggested, another one is a tap", async () => {
    await expect(page.getByRole("heading", { name: "¿Qué día salen tus cuentas?" })).toBeVisible();
    await expect(page.getByRole("radio", { name: /Día 1 Sugerido/ })).toHaveAttribute(
      "data-state",
      "on",
    );
    await page.getByRole("radio", { name: "Día 15" }).click();
    await continueButton.click();
  });

  await test.step("the review shows every answer and the bill they make", async () => {
    await expect(page.getByRole("heading", { name: "¿Todo bien?" })).toBeVisible();
    await expect(page.getByRole("main").getByText("El 15 de cada mes")).toBeVisible();
    const bill = page.getByLabel("Vista previa del documento");
    await expect(bill).toContainText("Pagar a: Nequi al 3001234567");
    await expect(bill).toContainText("A nombre de Pilar Prueba, NIT 900.123.456-7");
    await expect(bill).toContainText("NIT 900.123.456-7");

    // An answer changes from here and comes back.
    await page.getByRole("link", { name: "Cambiar" }).last().click();
    await expect(page.getByRole("radio", { name: "Día 15" })).toHaveAttribute("data-state", "on");
    await page.getByRole("radio", { name: "Día 5" }).click();
    await continueButton.click();
    await expect(page.getByRole("main").getByText("El 5 de cada mes")).toBeVisible();
  });

  await test.step("then the property, and the data is in Ajustes", async () => {
    await page.getByRole("button", { name: "Seguir con mi inmueble" }).click();
    await expect(page.getByRole("heading", { name: "Configura tu primer inmueble" })).toBeVisible();

    await page.goto("/settings");
    await expect(page.getByLabel("Cómo te pagan")).toHaveValue(PAYMENT);
    await expect(page.getByLabel("Número de NIT")).toHaveValue("900.123.456-7");
  });
});
