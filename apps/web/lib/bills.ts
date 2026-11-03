import type { components } from "@/lib/api/schema";

type Bill = components["schemas"]["BillSummary"];

/** The month a bill belongs to (`2026-10`): its period, or when it is due if it is manual. */
export const monthOf = (bill: Bill) => (bill.period ?? bill.due_date).slice(0, 7);

/** The first day of the month `count - 1` months before the one of `today` (`2026-05-01`). */
export function firstDayMonthsAgo(today: string, count: number): string {
  const [year, month] = today.split("-").map(Number);
  const index = year * 12 + (month - 1) - (count - 1);
  return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, "0")}-01`;
}

/** A month (`2026-10`, or a date in it) moved by `delta` months, as `2026-09`. */
export function shiftMonth(month: string, delta: number): string {
  const [year, number] = month.split("-").map(Number);
  const index = year * 12 + (number - 1) + delta;
  return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, "0")}`;
}

/** The month asked for in the address (`?month=2026-09`), or nothing if it is not one. */
export function monthParam(value: string | string[] | undefined): string | undefined {
  return typeof value === "string" && /^\d{4}-(0[1-9]|1[0-2])$/.test(value) ? value : undefined;
}

export type BillSort = { by: "due" | "status"; direction: "asc" | "desc" };

// From what has to be collected first to what needs nothing.
const URGENCY: Bill["status"][] = ["overdue", "partial", "pending", "paid", "voided"];

/**
 * The bills in the order asked for, as a new list. The direction turns only the column
 * chosen: on a tie, the same due date shows the newest bill first, and the same status
 * shows first the one that has been due longest.
 */
export function sortBills(bills: Bill[], sort: BillSort): Bill[] {
  const sign = sort.direction === "asc" ? 1 : -1;
  const byDue = (a: Bill, b: Bill) => a.due_date.localeCompare(b.due_date);
  return [...bills].sort((a, b) =>
    sort.by === "due"
      ? sign * byDue(a, b) || b.number - a.number
      : sign * (URGENCY.indexOf(a.status) - URGENCY.indexOf(b.status)) || byDue(a, b),
  );
}

/** The order after a click on a column: up, then down, then none, back to the months. */
export function nextSort(sort: BillSort | null, by: BillSort["by"]): BillSort | null {
  if (sort?.by !== by) return { by, direction: "asc" };
  return sort.direction === "asc" ? { by, direction: "desc" } : null;
}
