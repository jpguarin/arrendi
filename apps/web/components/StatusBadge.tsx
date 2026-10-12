import { Ban, Check, Clock, Contrast, KeyRound, TriangleAlert, type LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { components } from "@/lib/api/schema";
import { BILL_STATUS, type BillStatus, UNIT_STATUS } from "@/lib/labels";

type UnitStatus = components["schemas"]["UnitResponse"]["status"];

// The icon is the second cue next to the label, so a status never rests on color alone.
const BILL_ICONS: Record<BillStatus, LucideIcon> = {
  pending: Clock,
  partial: Contrast,
  paid: Check,
  overdue: TriangleAlert,
  voided: Ban,
};

const UNIT_ICONS: Record<UnitStatus, LucideIcon> = {
  up_to_date: Check,
  partial: Contrast,
  overdue: TriangleAlert,
  vacant: KeyRound,
};

/** The status of a bill: icon and label. */
export function BillStatusBadge({ status }: { status: BillStatus }) {
  const { label, tone } = BILL_STATUS[status];
  const Icon = BILL_ICONS[status];
  return (
    <Badge tone={tone}>
      <Icon aria-hidden strokeWidth={2.5} />
      {label}
    </Badge>
  );
}

/** How a unit is doing: icon and label. */
export function UnitStatusBadge({ status }: { status: UnitStatus }) {
  const { label, tone } = UNIT_STATUS[status];
  const Icon = UNIT_ICONS[status];
  return (
    <Badge tone={tone}>
      <Icon aria-hidden strokeWidth={2.5} />
      {label}
    </Badge>
  );
}

/** The color of the bar at the start of a row, by tone. */
export const TONE_BAR = {
  positive: "before:bg-positive",
  warning: "before:bg-warning",
  info: "before:bg-info",
  alert: "before:bg-alert",
  neutral: "before:bg-neutral",
} as const;
