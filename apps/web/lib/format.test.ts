import assert from "node:assert/strict";
import { test } from "node:test";

import { formatDate, formatDateTime, formatPesos, parsePesos } from "./format.ts";

test("pesos have a dot every three digits and no decimals", () => {
  assert.equal(formatPesos(0), "$0");
  assert.equal(formatPesos(950), "$950");
  assert.equal(formatPesos(1000), "$1.000");
  assert.equal(formatPesos(950000), "$950.000");
  assert.equal(formatPesos(1000000), "$1.000.000");
  assert.equal(formatPesos(2650000), "$2.650.000");
  assert.equal(formatPesos(1234567890), "$1.234.567.890");
});

test("a negative amount keeps its sign before the peso sign", () => {
  assert.equal(formatPesos(-1500), "-$1.500");
});

test("typed money is read as whole pesos, whatever the owner adds around the digits", () => {
  assert.equal(parsePesos("$950.000"), 950000);
  assert.equal(parsePesos("950000"), 950000);
  assert.equal(parsePesos(" 1.000.000 "), 1000000);
  assert.equal(parsePesos("$0"), 0);
});

test("a money field without digits is empty, not zero", () => {
  assert.equal(parsePesos(""), null);
  assert.equal(parsePesos("$"), null);
  assert.equal(parsePesos("abc"), null);
});

test("what is shown reads back as the same amount", () => {
  for (const amount of [0, 5, 950000, 1000000, 123456789]) {
    assert.equal(parsePesos(formatPesos(amount)), amount);
  }
});

test("dates are day, short month and year", () => {
  assert.equal(formatDate("2026-10-05"), "5 oct 2026");
  assert.equal(formatDate("2026-01-01"), "1 ene 2026");
  assert.equal(formatDate("2026-12-31"), "31 dic 2026");
  assert.equal(formatDate("2027-09-15"), "15 sep 2027");
});

test("a business date does not move with the time zone", () => {
  // The first of the month must not become the last day of the month before.
  assert.equal(formatDate("2026-03-01"), "1 mar 2026");
});

test("an instant is shown as its date in Colombia", () => {
  // 3:00 UTC on the 5th is still the 4th at 22:00 in Bogotá.
  assert.equal(formatDateTime("2026-10-05T03:00:00Z"), "4 oct 2026");
  assert.equal(formatDateTime("2026-10-05T05:00:00+00:00"), "5 oct 2026");
  assert.equal(formatDateTime("2026-10-05T15:30:00.123456Z"), "5 oct 2026");
});
