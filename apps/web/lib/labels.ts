import type { components } from "@/lib/api/schema";

type Schemas = components["schemas"];
export type PropertyType = Schemas["PropertyCreate"]["type"];
export type UnitUse = Schemas["UnitCreate"]["use"];
export type BillStatus = Schemas["BillSummary"]["status"];

// What the owner reads for each value the API stores in English.
export const PROPERTY_TYPE_LABELS: Record<PropertyType, string> = {
  house: "Casa",
  building: "Edificio",
  apartment: "Apartamento",
  shop: "Local",
};

export const UNIT_USE_LABELS: Record<UnitUse, string> = {
  residential: "Vivienda",
  commercial: "Comercial",
};

// The status is always said with text; the tone only supports it (docs/diseno.md).
export const BILL_STATUS: Record<
  BillStatus,
  { label: string; tone: "positive" | "alert" | "info" | "neutral" }
> = {
  pending: { label: "Pendiente", tone: "neutral" },
  partial: { label: "Parcial", tone: "info" },
  paid: { label: "Pagada", tone: "positive" },
  overdue: { label: "Vencida", tone: "alert" },
  voided: { label: "Anulada", tone: "neutral" },
};

export const PROPERTY_TYPE_OPTIONS = (Object.keys(PROPERTY_TYPE_LABELS) as PropertyType[]).map(
  (value) => ({ value, label: PROPERTY_TYPE_LABELS[value] }),
);

export const UNIT_USE_OPTIONS = (Object.keys(UNIT_USE_LABELS) as UnitUse[]).map((value) => ({
  value,
  label: UNIT_USE_LABELS[value],
}));

// Provisional: 29 to 31 are left out so the day exists in every month.
export const DUE_DAY_OPTIONS = Array.from({ length: 28 }, (_, index) => ({
  value: String(index + 1),
  label: `${index + 1} del mes`,
}));
