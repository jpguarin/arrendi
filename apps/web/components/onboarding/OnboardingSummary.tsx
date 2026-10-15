"use client";

import { Check } from "lucide-react";

import { Button } from "@/components/ui/button";
import { formatPesos } from "@/lib/format";
import { PROPERTY_TYPE_LABELS } from "@/lib/labels";
import { cn } from "@/lib/utils";

import { type Draft, useOnboarding } from "./OnboardingContext";
import { LEASE_FORM_ID } from "./LeaseStep";

type Line = { done: boolean; title: string; detail: string };

/** A unit count as the owner says it: "1 unidad", "3 unidades". */
function unitCount(count: number): string {
  return `${count} ${count === 1 ? "unidad" : "unidades"}`;
}

function leaseLine(draft: Draft): Line {
  if (!draft.withLease) {
    return { done: Boolean(draft.units), title: "Sin contrato por ahora", detail: "Lo agregas desde la unidad" };
  }
  const lease = draft.lease ?? {};
  const unit = lease.unit !== undefined ? draft.units?.[Number(lease.unit)]?.name : undefined;
  const parts = [lease.tenant_name, unit, lease.rent ? formatPesos(lease.rent) : undefined];
  const detail = parts.filter(Boolean).join(" · ");
  const complete = Boolean(
    lease.tenant_name && lease.tenant_email && lease.rent && lease.due_day && lease.start_date,
  );
  return { done: complete, title: "Primer contrato", detail: detail || "Arrendatario y canon" };
}

/** What the sheet will create, part by part, as it gets confirmed. */
function lines(draft: Draft): Line[] {
  const { property, units } = draft;
  return [
    {
      done: Boolean(property),
      title: property?.name || "Tu inmueble",
      detail: property ? PROPERTY_TYPE_LABELS[property.type] : "Nombre y tipo",
    },
    {
      done: Boolean(units),
      title: units ? unitCount(units.length) : "Unidades",
      detail: units?.map((unit) => unit.name).join(", ") || "Sus nombres y uso",
    },
    leaseLine(draft),
  ];
}

type OnboardingSummaryProps = {
  /** Creating is only possible from the last part, once the first two are confirmed. */
  canCreate: boolean;
};

/** "Lo que vas a crear": next to the sheet from the tablet up. */
export function OnboardingSummary({ canCreate }: OnboardingSummaryProps) {
  const { draft, creating } = useOnboarding();

  return (
    <aside
      aria-label="Lo que vas a crear"
      className="hidden flex-col gap-4 rounded-xl border border-border bg-card p-5 md:sticky md:top-6 md:flex"
    >
      <h2 className="font-heading text-title-back font-extrabold">Lo que vas a crear</h2>
      <ul className="flex flex-col">
        {lines(draft).map((line, index) => (
          <li
            key={index}
            className="grid grid-cols-[1.375rem_minmax(0,1fr)] gap-2.5 border-t border-border py-2.5 first:border-t-0"
          >
            <span
              className={cn(
                "mt-0.5 grid size-5.5 place-items-center rounded-full border-[1.5px]",
                line.done ? "border-transparent bg-positive-tint text-positive-ink" : "border-input text-transparent",
              )}
            >
              <Check aria-hidden className="size-3.5" />
              <span className="sr-only">{line.done ? "Listo" : "Falta"}</span>
            </span>
            <span className="flex min-w-0 flex-col text-support">
              <span className="font-semibold">{line.title}</span>
              <span className="text-muted-foreground">{line.detail}</span>
            </span>
          </li>
        ))}
      </ul>
      <Button type="submit" form={LEASE_FORM_ID} disabled={!canCreate || creating}>
        {creating ? "Creando…" : "Crear inmueble"}
      </Button>
      <p className="text-support text-muted-foreground">
        {canCreate
          ? "Se crea todo junto. Hasta entonces no se guarda nada."
          : "Confirma cada parte con «Continuar» para poder crearlo."}
      </p>
    </aside>
  );
}

/** The same summary on a phone: one line and the button, fixed at the bottom. */
export function OnboardingSummaryFooter() {
  const { draft, creating } = useOnboarding();
  const units = draft.units?.length ?? 0;

  return (
    <footer className="sticky bottom-0 flex items-center gap-3 border-t border-border bg-card px-4 pt-3 pb-[max(1.75rem,calc(env(safe-area-inset-bottom)+0.75rem))] md:hidden">
      <p className="min-w-0 flex-1 text-support text-muted-foreground">
        <span className="block truncate font-semibold text-foreground">{draft.property?.name}</span>
        {unitCount(units)} · {draft.withLease ? "1 contrato" : "sin contrato"}
      </p>
      <Button type="submit" form={LEASE_FORM_ID} disabled={creating}>
        {creating ? "Creando…" : "Crear inmueble"}
      </Button>
    </footer>
  );
}
