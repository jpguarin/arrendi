import assert from "node:assert/strict";
import { test } from "node:test";

import { firstDayMonthsAgo } from "./bills.ts";

test("the window of months starts on the first day, across a year", () => {
  assert.equal(firstDayMonthsAgo("2026-10-12", 6), "2026-05-01");
  assert.equal(firstDayMonthsAgo("2026-10-12", 1), "2026-10-01");
  assert.equal(firstDayMonthsAgo("2026-03-31", 6), "2025-10-01");
  assert.equal(firstDayMonthsAgo("2026-01-01", 2), "2025-12-01");
});
