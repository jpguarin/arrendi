import assert from "node:assert/strict";
import { test } from "node:test";

import { isConfirmableOtpType, safeNextPath } from "./navigation.ts";

const BASE = "https://arrendi.example/auth/confirm";

test("safeNextPath keeps a path inside the app", () => {
  assert.equal(safeNextPath("/"), "/");
  assert.equal(safeNextPath("/update-password"), "/update-password");
  assert.equal(safeNextPath("/bills?status=paid#top"), "/bills?status=paid#top");
});

test("safeNextPath sends anything missing or absolute to the home screen", () => {
  for (const next of [null, "", "bills", "https://evil.example", "javascript:alert(1)"]) {
    assert.equal(safeNextPath(next), "/", String(next));
  }
});

test("safeNextPath never leaves the app, however the path is disguised", () => {
  const disguised = [
    "//evil.example",
    "///evil.example",
    "/\\evil.example",
    "/\\/evil.example",
    // A URL parser drops tabs and line breaks, which turns these into //evil.example.
    "/\t/evil.example",
    "/\n/evil.example",
    "/\r/evil.example",
    "/\t\\evil.example",
  ];
  for (const next of disguised) {
    const safe = safeNextPath(next);
    assert.equal(safe, "/", JSON.stringify(next));
    assert.equal(new URL(safe, BASE).origin, new URL(BASE).origin, JSON.stringify(next));
  }
});

test("isConfirmableOtpType accepts only the links Arrendi's emails carry", () => {
  for (const type of ["email", "signup", "recovery", "invite"]) {
    assert.equal(isConfirmableOtpType(type), true, type);
  }
  for (const type of [null, "", "magiclink", "email_change", "phone", "RECOVERY"]) {
    assert.equal(isConfirmableOtpType(type), false, String(type));
  }
});
