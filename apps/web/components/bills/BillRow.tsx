"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { BillStatusBadge, TONE_BAR } from "@/components/StatusBadge";
import type { components } from "@/lib/api/schema";
import {
  daysBetween,
  formatBillNumber,
  formatDayMonth,
  formatPesos,
  todayInBogota,
} from "@/lib/format";
import { BILL_STATUS } from "@/lib/labels";
import { cn } from "@/lib/utils";

type Bill = components["schemas"]["BillSummary"];

// The columns of a wide table: who, number (only when there is room), due, amount, status.
const COLUMNS =
  "@row:grid-cols-[minmax(0,1.6fr)_6.5rem_7.5rem_7.25rem] @row-wide:grid-cols-[minmax(0,1.6fr)_5.5rem_6.5rem_7.5rem_7.25rem] @row:gap-x-3";

/** What matters about the bill right now, next to its due date or its number. */
function situation(bill: Bill): string {
  if (bill.status === "voided") return "anulada";
  if (bill.status === "paid") {
    return bill.last_payment_date ? `pagó el ${formatDayMonth(bill.last_payment_date)}` : "pagada";
  }
  // With a payment on it, what came in matters more than when it is due.
  if (bill.balance < bill.total) return `abonó ${formatPesos(bill.total - bill.balance)}`;
  if (bill.status === "overdue") {
    const days = daysBetween(bill.due_date, todayInBogota());
    return days === 1 ? "venció hace 1 día" : `venció hace ${days} días`;
  }
  return `vence el ${formatDayMonth(bill.due_date)}`;
}

/**
 * A table of bills: a card that lays its rows out by its own width, so the same table
 * works full width and squeezed next to an open detail.
 */
export function BillTable({
  amountLabel = "Valor",
  withActions = false,
  children,
}: {
  amountLabel?: string;
  /** Leaves room in the headings for the buttons of each row. */
  withActions?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="@container overflow-hidden rounded-xl border border-border bg-card">
      <div
        aria-hidden
        className={cn(
          "hidden border-b border-border py-2.5 pr-3.5 pl-4 text-badge font-semibold text-muted-foreground @row:grid",
          COLUMNS,
          withActions && "@row:mr-48",
        )}
      >
        <span>Unidad y arrendatario</span>
        <span className="hidden @row-wide:block">Cuenta</span>
        <span>Vence</span>
        <span className="text-right">{amountLabel}</span>
        <span>Estado</span>
      </div>
      <ul>{children}</ul>
    </div>
  );
}

/** The heading of a group of rows inside a table, like a month. */
export function BillGroup({ title, detail }: { title: string; detail: string }) {
  return (
    <li className="flex items-baseline justify-between gap-3 border-t border-border bg-muted px-4 py-2.5 first:border-t-0">
      <h2 className="font-heading text-section font-extrabold">{title}</h2>
      <p className="text-right text-support text-muted-foreground">{detail}</p>
    </li>
  );
}

/**
 * A bill in a table: who owes, how much and its status. The row opens the bill.
 * `actions` are the buttons of the row: beside it when there is room, under it when not.
 */
export function BillRow({ bill, actions }: { bill: Bill; actions?: React.ReactNode }) {
  const pathname = usePathname();
  const open = pathname === `/bills/${bill.id}` || pathname.startsWith(`/bills/${bill.id}/`);
  const owed = bill.status !== "paid" && bill.status !== "voided";

  return (
    <li
      className={cn(
        "relative flex flex-col border-t border-border before:absolute before:inset-y-2 before:left-0 before:w-0.75 before:rounded-r-full first:border-t-0 @row:flex-row @row:items-stretch",
        TONE_BAR[BILL_STATUS[bill.status].tone],
      )}
    >
      <Link
        href={`/bills/${bill.id}`}
        aria-current={open ? "true" : undefined}
        className={cn(
          "grid min-h-14 min-w-0 flex-1 grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-0.5 py-2 pr-3.5 pl-4 outline-none hover:bg-muted focus-visible:bg-muted @row:min-h-12",
          COLUMNS,
          open && "bg-accent hover:bg-accent",
        )}
      >
        <span className="truncate text-section font-semibold">
          {bill.unit_name} <span className="font-normal text-muted-foreground">· {bill.tenant_name}</span>
        </span>
        <span className="hidden text-support text-muted-foreground @row-wide:block">
          {formatBillNumber(bill.number)}
        </span>
        <span className="hidden flex-col text-support @row:flex">
          {formatDayMonth(bill.due_date)}
          {/* Under the date, what makes this bill urgent: it is late, or half paid. */}
          {owed && (bill.status === "overdue" || bill.balance < bill.total) && (
            <span className="text-badge text-muted-foreground">{situation(bill)}</span>
          )}
        </span>
        <span className="text-right text-section font-semibold whitespace-nowrap">
          {formatPesos(owed ? bill.balance : bill.total)}
          {owed && bill.balance < bill.total && (
            <span className="ml-1 text-badge font-normal text-muted-foreground">saldo</span>
          )}
        </span>
        <span className="truncate text-support text-muted-foreground @row:hidden">
          {formatBillNumber(bill.number)} · {situation(bill)}
        </span>
        <span className="justify-self-end @row:justify-self-start">
          <BillStatusBadge status={bill.status} />
        </span>
      </Link>
      {actions && (
        <div className="flex items-center gap-1.5 px-4 pb-3 *:flex-1 @row:w-48 @row:shrink-0 @row:justify-end @row:py-0 @row:pr-3 @row:pl-0 @row:*:flex-none">
          {actions}
        </div>
      )}
    </li>
  );
}
