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
