"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useMe } from "@/lib/api/queries";
import { PROPERTY_TYPE_LABELS } from "@/lib/labels";

import { LeaseStep } from "./LeaseStep";
import { type Draft, useOnboarding } from "./OnboardingContext";
import { OnboardingSection, type SectionState } from "./OnboardingSection";
import { OnboardingSummary, OnboardingSummaryFooter } from "./OnboardingSummary";
import { PropertyStep } from "./PropertyStep";
import { UnitsStep } from "./UnitsStep";

export type Part = "property" | "units" | "lease";

/** The route of each part: the sheet is one, and the route says which part is open. */
const HREF: Record<Part, string> = {
  property: "/onboarding/property",
  units: "/onboarding/units",
  lease: "/onboarding/lease",
};

/** The first part that has not been confirmed yet. */
function firstMissing(draft: Draft): Part | null {
  if (!draft.property) return "property";
  if (!draft.units) return "units";
  return null;
}

/** "Hola, Carolina": the first word of the name, which may be an email if there is none. */
function firstName(name: string): string {
  return name.split(" ")[0];
}

/**
 * The onboarding as one sheet with three parts. A confirmed part folds into a line with
 * what it holds, and "Editar" opens it again. From the tablet up, a summary next to it
 * says what will be created.
 */
export function OnboardingSheet({ open }: { open: Part }) {
  const router = useRouter();
  const { data: me } = useMe();
  const { draft, ready } = useOnboarding();

  // A part opens only once the ones before it are confirmed (an old link, a reload).
  const missing = firstMissing(draft);
  const order: Part[] = ["property", "units", "lease"];
  const blocked = missing !== null && order.indexOf(open) > order.indexOf(missing);
  useEffect(() => {
    if (ready && blocked && missing) router.replace(HREF[missing]);
  }, [ready, blocked, missing, router]);
  if (!ready || blocked) return null;

  const state = (part: Part): SectionState => {
    if (part === open) return "open";
    const confirmed = part === "property" ? draft.property : part === "units" ? draft.units : null;
    return confirmed ? "done" : "waiting";
  };
  const { property, units, lease } = draft;
  const leaseUnit = lease?.unit !== undefined ? units?.[Number(lease.unit)]?.name : undefined;

  return (
    <>
      <div className="mx-auto grid w-full max-w-sheet flex-1 items-start gap-6 px-4 pt-6 pb-8 md:grid-cols-[minmax(0,1fr)_17.5rem] md:px-6 md:pt-8 lg:grid-cols-[minmax(0,1fr)_21.25rem] lg:gap-8 lg:px-8 lg:pt-10">
        <main className="flex min-w-0 flex-col gap-3">
          <div className="mb-3 flex flex-col gap-1.5">
            {me && (
              <p className="text-body font-semibold text-foreground-soft">
                Hola, {firstName(me.name)}
              </p>
            )}
            <h1 className="text-title-onboarding leading-tight font-bold">
              Configura tu primer inmueble
            </h1>
            <p className="text-section text-muted-foreground">
              Tres partes en una sola hoja. Puedes volver a cualquiera antes de crearlo.
            </p>
          </div>
          <OnboardingSection
            step={1}
            title="Inmueble"
            hint="Nombre, tipo y dirección"
            summary={[property?.name, property && PROPERTY_TYPE_LABELS[property.type], property?.city]
              .filter(Boolean)
              .join(" · ")}
            state={state("property")}
            href={HREF.property}
          >
            <PropertyStep />
          </OnboardingSection>
          <OnboardingSection
            step={2}
            title="Unidades"
            hint="Cada espacio que cobras por separado"
            summary={units?.map((unit) => unit.name).join(", ") ?? ""}
            state={state("units")}
            href={HREF.units}
          >
            <UnitsStep />
          </OnboardingSection>
          <OnboardingSection
            step={3}
            title="Primer contrato"
            hint="Opcional: arrendatario, canon y fechas"
            summary={
              draft.withLease
                ? [lease?.tenant_name, leaseUnit].filter(Boolean).join(" · ")
                : "Lo agregas después"
            }
            state={state("lease")}
            href={HREF.lease}
          >
            <LeaseStep />
          </OnboardingSection>
        </main>
        <OnboardingSummary canCreate={open === "lease"} />
      </div>
      {open === "lease" && <OnboardingSummaryFooter />}
    </>
  );
}
