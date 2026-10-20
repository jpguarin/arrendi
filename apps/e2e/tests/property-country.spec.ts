import { expect, test } from "@playwright/test";

import { fillProfile, setUpHouse } from "./onboarding";

// A property is in Colombia unless the owner says otherwise. Only another country is
// worth saying next to the city.

test("a property starts in Colombia and can be moved to another country", async ({ page }) => {
  await test.step("sign in and set up a house, in Colombia without choosing it", async () => {
    await page.goto("/login");
    await page.getByLabel("Correo").fill("ines.prueba@example.com");
    await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
    await page.getByRole("button", { name: "Ingresar" }).click();
    await fillProfile(page);
    await expect(page.getByRole("combobox", { name: "País" })).toHaveText("Colombia");

    await setUpHouse(
      page,
      {
        property: "Casa Sur",
        unit: "Apto 5",
        tenant: "Rosa Díaz",
        email: "rosa.diaz@example.com",
        rent: "800000",
      },
      { profileDone: true },
    );
  });

  await test.step("in Colombia, the list does not say so", async () => {
    await page.getByRole("link", { name: "Inmuebles" }).click();
    await page.getByRole("link", { name: "Editar Casa Sur" }).click();
    await page.getByLabel("Ciudad").fill("Medellín");
    await page.getByRole("button", { name: "Guardar cambios" }).click();

    await expect(page.getByText("Casa · Medellín", { exact: true })).toBeVisible();
    await expect(page.getByText("Colombia")).toHaveCount(0);
  });

  await test.step("moved to Panamá, the list says it next to the city", async () => {
    await page.getByRole("link", { name: "Editar Casa Sur" }).click();
    await expect(page.getByRole("combobox", { name: "País" })).toHaveText("Colombia");
    await page.getByLabel("Ciudad").fill("Ciudad de Panamá");
    await page.getByRole("combobox", { name: "País" }).click();
    await page.getByRole("option", { name: "Panamá", exact: true }).click();
    await page.getByRole("button", { name: "Guardar cambios" }).click();

    await expect(page.getByText("Casa · Ciudad de Panamá · Panamá")).toBeVisible();
    // And the form opens again with it.
    await page.getByRole("link", { name: "Editar Casa Sur" }).click();
    await expect(page.getByRole("combobox", { name: "País" })).toHaveText("Panamá");
  });
});
