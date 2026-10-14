import assert from "node:assert/strict";
import { test } from "node:test";

import { appEnvironment } from "./environment.ts";

test("production and preview keep their name", () => {
  assert.equal(appEnvironment("production"), "production");
  assert.equal(appEnvironment("preview"), "preview");
});

test("anything else is this computer", () => {
  assert.equal(appEnvironment("development"), "local");
  assert.equal(appEnvironment("local"), "local");
  assert.equal(appEnvironment(undefined), "local");
  assert.equal(appEnvironment(""), "local");
  assert.equal(appEnvironment("Production"), "local");
});
