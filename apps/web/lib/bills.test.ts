import assert from "node:assert/strict";
import { test } from "node:test";

import type { components } from "./api/schema.ts";
import { firstDayMonthsAgo, nextSort, sortBills } from "./bills.ts";

type Bill = components["schemas"]["BillSummary"];

test("the window of months starts on the first day, across a year", () => {
  assert.equal(firstDayMonthsAgo("2026-10-12", 6), "2026-05-01");
  assert.equal(firstDayMonthsAgo("2026-10-12", 1), "2026-10-01");
  assert.equal(firstDayMonthsAgo("2026-03-31", 6), "2025-10-01");
  assert.equal(firstDayMonthsAgo("2026-01-01", 2), "2025-12-01");
});

// Only what the order looks at; the rest of a bill does not matter here.
const bill = (number: number, due_date: string, status: Bill["status"]) =>
  ({ id: `b${number}`, number, due_date, status }) as Bill;

const numbers = (bills: Bill[]) => bills.map((each) => each.number);

const BILLS = [
  bill(4, "2026-10-05", "pending"),
  bill(1, "2026-09-05", "overdue"),
  bill(6, "2026-10-05", "paid"),
  bill(3, "2026-09-20", "partial"),
  bill(2, "2026-08-05", "overdue"),
  bill(5, "2026-10-05", "voided"),
];

test("by due date, the oldest first, and on the same day the newest bill first", () => {
  assert.deepEqual(numbers(sortBills(BILLS, { by: "due", direction: "asc" })), [2, 1, 3, 6, 5, 4]);
});

test("by due date the other way, the latest first, still the newest bill first on a tie", () => {
  assert.deepEqual(numbers(sortBills(BILLS, { by: "due", direction: "desc" })), [6, 5, 4, 3, 1, 2]);
});

test("by status, the most urgent first, and the longest overdue first among the same", () => {
  assert.deepEqual(numbers(sortBills(BILLS, { by: "status", direction: "asc" })), [2, 1, 3, 4, 6, 5]);
});

test("by status the other way, the least urgent first, ties still by due date", () => {
  assert.deepEqual(numbers(sortBills(BILLS, { by: "status", direction: "desc" })), [5, 6, 4, 3, 2, 1]);
});

test("sorting leaves the list it was given as it was", () => {
  const before = numbers(BILLS);
  sortBills(BILLS, { by: "status", direction: "asc" });
  assert.deepEqual(numbers(BILLS), before);
});

test("each click on a column goes up, then down, then back to the months", () => {
  const up = nextSort(null, "due");
  assert.deepEqual(up, { by: "due", direction: "asc" });
  const down = nextSort(up, "due");
  assert.deepEqual(down, { by: "due", direction: "desc" });
  assert.equal(nextSort(down, "due"), null);
  // Another column starts again from the top.
  assert.deepEqual(nextSort(down, "status"), { by: "status", direction: "asc" });
});
