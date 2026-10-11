import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import type { components } from "@/lib/api/schema";
import { formatBillNumber, formatDayMonth, formatPesos } from "@/lib/format";
import { BILL_STATUS } from "@/lib/labels";

type Bill = components["schemas"]["BillSummary"];

/** What matters about the bill right now, next to its number. */
function situation(bill: Bill): string {
  if (bill.status === "voided") return "anulada";
  if (bill.status === "paid") return "pagada";
  const due = formatDayMonth(bill.due_date);
  return bill.status === "overdue" ? `venció el ${due}` : `vence el ${due}`;
}

/** A bill in a list: who owes on the left, how much and its status on the right. */
export function BillRow({ bill }: { bill: Bill }) {
  const status = BILL_STATUS[bill.status];

  return (
    <li className="border-t border-border first:border-t-0">
      <Link
        href={`/bills/${bill.id}`}
        className="flex min-h-16 items-center justify-between gap-2.5 py-2 outline-none focus-visible:bg-muted"
      >
        <span className="flex min-w-0 flex-col gap-0.5">
          <span className="truncate text-section font-semibold">
            {bill.unit_name} · {bill.tenant_name}
          </span>
          <span className="truncate text-support text-muted-foreground">
            {formatBillNumber(bill.number)} · {situation(bill)}
          </span>
        </span>
        <span className="flex shrink-0 flex-col items-end gap-1">
          <span className="text-section font-bold">{formatPesos(bill.total)}</span>
          <Badge tone={status.tone}>{status.label}</Badge>
        </span>
      </Link>
    </li>
  );
}
