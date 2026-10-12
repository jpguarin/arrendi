import type { components } from "@/lib/api/schema";

type Schemas = components["schemas"];
export type PropertyType = Schemas["PropertyCreate"]["type"];
export type UnitUse = Schemas["UnitCreate"]["use"];
export type DocumentType = Schemas["SettingsResponse"]["document_type"];
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

// How a bill names the owner's document, and how Ajustes offers the choice.
export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = { cc: "C.C.", nit: "NIT" };

export const DOCUMENT_TYPE_OPTIONS: { value: DocumentType; label: string }[] = [
  { value: "cc", label: "Cédula" },
  { value: "nit", label: "NIT" },
];

// For a tenant the NIT comes first and is what the form starts on, while no document
// number has been saved. The API's own default is the cédula.
export const TENANT_DOCUMENT_TYPE: DocumentType = "nit";
export const TENANT_DOCUMENT_TYPE_OPTIONS = [...DOCUMENT_TYPE_OPTIONS].reverse();

export type StatusTone = "positive" | "warning" | "info" | "alert" | "neutral";

// The status is always said with text; the tone only supports it (docs/diseno.md).
export const BILL_STATUS: Record<
  BillStatus,
  { label: string; tone: StatusTone }
> = {
  pending: { label: "Pendiente", tone: "info" },
  partial: { label: "Parcial", tone: "warning" },
  paid: { label: "Pagada", tone: "positive" },
  overdue: { label: "Vencida", tone: "alert" },
  voided: { label: "Anulada", tone: "neutral" },
};

export type PaymentMethod = Schemas["PaymentCreate"]["method"];

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  transfer: "Transferencia",
  nequi: "Nequi",
  cash: "Efectivo",
  other: "Otro",
};

export const PAYMENT_METHOD_OPTIONS = (
  Object.keys(PAYMENT_METHOD_LABELS) as PaymentMethod[]
).map((value) => ({ value, label: PAYMENT_METHOD_LABELS[value] }));

type Notification = Schemas["NotificationResponse"];

// What each email was, as the activity of a bill tells it.
export const NOTIFICATION_LABELS: Record<Notification["type"], string> = {
  bill: "Enviada por correo con el PDF",
  resend: "Reenviada por correo",
  reminder_1: "Recordatorio por correo",
  reminder_2: "Segundo recordatorio por correo",
  manual_reminder: "Recordatorio por correo",
  receipt: "Recibo por correo",
};

// How it went, when it did not simply go out.
export const DELIVERY_PROBLEMS: Partial<Record<Notification["delivery_status"], string>> = {
  pending: "enviando…",
  failed: "no se pudo enviar",
  bounced: "rebotó",
};

type Unit = Schemas["UnitResponse"];

// How each unit is doing, from what its active lease still owes.
export const UNIT_STATUS: Record<Unit["status"], { label: string; tone: StatusTone }> = {
  up_to_date: { label: "Al día", tone: "positive" },
  overdue: { label: "En mora", tone: "alert" },
  partial: { label: "Pago parcial", tone: "warning" },
  vacant: { label: "Vacía", tone: "neutral" },
};

// The day of the month the bills go out.
export const SEND_DAY_OPTIONS = Array.from({ length: 28 }, (_, index) => ({
  value: String(index + 1),
  label: `El día ${index + 1} de cada mes`,
}));

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
