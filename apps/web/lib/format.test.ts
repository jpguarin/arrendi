import assert from "node:assert/strict";
import { test } from "node:test";

import {
  daysBetween,
  formatBillNumber,
  formatDate,
  formatDateHour,
  formatDateTime,
  formatDayMonth,
  formatLongDate,
  formatMonth,
  formatPercent,
  formatPesos,
  parsePercent,
  parsePesos,
  percentOf,
  todayInBogota,
} from "./format.ts";

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

test("today is the day in Colombia, not in UTC", () => {
  // 2:00 UTC on the 1st is still the 31st at 21:00 in Bogotá.
  assert.equal(todayInBogota(new Date("2026-11-01T02:00:00Z")), "2026-10-31");
  assert.equal(todayInBogota(new Date("2026-11-01T05:00:00Z")), "2026-11-01");
});

test("a bill number has at least four digits", () => {
  assert.equal(formatBillNumber(1), "N.º 0001");
  assert.equal(formatBillNumber(31), "N.º 0031");
  assert.equal(formatBillNumber(12345), "N.º 12345");
});

test("a month is written with its name and year", () => {
  assert.equal(formatMonth("2026-10-01"), "Octubre 2026");
  assert.equal(formatMonth("2026-10"), "Octubre 2026");
  assert.equal(formatMonth("2027-01-01", "short"), "Ene 2027");
});

test("a date can be written long, or short without its year", () => {
  assert.equal(formatLongDate("2026-10-05"), "5 de octubre de 2026");
  assert.equal(formatDayMonth("2026-10-05"), "5 oct");
});

test("days between two business dates, across months and years", () => {
  assert.equal(daysBetween("2026-10-05", "2026-10-10"), 5);
  assert.equal(daysBetween("2026-10-05", "2026-10-05"), 0);
  assert.equal(daysBetween("2026-10-05", "2026-10-03"), -2);
  assert.equal(daysBetween("2026-12-30", "2027-01-02"), 3);
});

test("an instant is written with its hour in Colombia", () => {
  assert.equal(formatDateHour("2026-10-05T20:42:00Z"), "5 oct 2026 · 3:42 p. m.");
  assert.equal(formatDateHour("2026-10-05T12:00:00Z"), "5 oct 2026 · 7:00 a. m.");
  // Midnight in Colombia is still the day before in UTC terms, and reads as 12.
  assert.equal(formatDateHour("2026-10-06T05:05:00Z"), "6 oct 2026 · 12:05 a. m.");
  assert.equal(formatDateHour("2026-10-05T17:30:00Z"), "5 oct 2026 · 12:30 p. m.");
});

test("a percentage is written with a comma and without the zeros it does not need", () => {
  assert.equal(formatPercent("5.00"), "5 %");
  assert.equal(formatPercent("2.50"), "2,5 %");
  assert.equal(formatPercent("1.25"), "1,25 %");
  assert.equal(formatPercent("100.00"), "100 %");
  assert.equal(formatPercent("10"), "10 %");
});

test("what the owner types as a percentage is read with a comma or a dot", () => {
  assert.equal(parsePercent("5"), "5");
  assert.equal(parsePercent("2,5"), "2.5");
  assert.equal(parsePercent("2.50"), "2.5");
  assert.equal(parsePercent(" 5 % "), "5");
  assert.equal(parsePercent("100"), "100");
});

test("a percentage has to be above zero, up to 100 and with two decimals at most", () => {
  for (const text of ["", "0", "0,00", "100,01", "2,555", "-5", "cinco", "1.000"]) {
    assert.equal(parsePercent(text), null, text);
  }
});

test("the late fee is a percentage of the rent in whole pesos", () => {
  assert.equal(percentOf(950000, "5"), 47500);
  assert.equal(percentOf(1000000, "2.5"), 25000);
  assert.equal(percentOf(1000020, "2.5"), 25001);
  assert.equal(percentOf(1234567, "2.5"), 30864);
});
