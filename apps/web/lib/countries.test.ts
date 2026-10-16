import assert from "node:assert/strict";
import { test } from "node:test";

import { COUNTRY_OPTIONS, countryName, otherCountry } from "./countries.ts";

test("every country has its name in Spanish", () => {
  assert.equal(countryName("CO"), "Colombia");
  assert.equal(countryName("PA"), "Panamá");
  assert.equal(countryName("CI"), "Costa de Marfil");
  assert.equal(countryName("HK"), "Hong Kong");
});

test("the list starts with Colombia and goes on in alphabetical order, accents and all", () => {
  const labels = COUNTRY_OPTIONS.map((option) => option.label);
  assert.equal(COUNTRY_OPTIONS.length, 249);
  assert.equal(COUNTRY_OPTIONS[0].value, "CO");
  assert.equal(labels.filter((label) => label === "Colombia").length, 1);
  const rest = labels.slice(1);
  assert.deepEqual(rest, [...rest].sort((a, b) => a.localeCompare(b, "es")));
  // Accented names sort with their letter, not after the Z.
  assert.ok(labels.indexOf("Islandia") < labels.indexOf("Italia"));
  assert.ok(labels.indexOf("Egipto") < labels.indexOf("Emiratos Árabes Unidos"));
});

test("only a country other than Colombia is worth saying next to the city", () => {
  assert.equal(otherCountry("CO"), undefined);
  assert.equal(otherCountry("PA"), "Panamá");
});
