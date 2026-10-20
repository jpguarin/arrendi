"use client";

import { Building2, Check, ChevronRight, UserPlus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { FormMessage } from "@/components/FormMessage";
import { Button } from "@/components/ui/button";
import { useMarkOnboarded, useMe } from "@/lib/api/queries";

import { useOnboarding } from "./OnboardingContext";

type NextStep = { href: string; icon: React.ReactNode; title: string; detail: string };

/** After creating everything: what was created and what can come next. */
export function OnboardingDone() {
  const router = useRouter();
  const { data: me } = useMe();
  const { draft, ready, outcome } = useOnboarding();
  const markOnboarded = useMarkOnboarded();

  // Only right after creating: opened any other way there is nothing to tell. Someone who
  // already finished goes home from the provider.
  const lost = ready && !outcome && me?.onboarding_complete === false;
  useEffect(() => {
    if (lost) router.replace("/onboarding/property");
  }, [lost, router]);
  if (!outcome || !draft.property || !draft.units) return null;

  const units = draft.units.length;
  const withoutLease = units - (outcome.leaseCreated ? 1 : 0);
  const tenant = draft.lease?.tenant_name;
  const steps: NextStep[] = [
    ...(withoutLease > 0
      ? [
          {
            href: "/properties",
            icon: <UserPlus />,
            title: outcome.leaseCreated ? "Agregar los demás contratos" : "Agregar los contratos",
            detail: `${withoutLease} ${withoutLease === 1 ? "unidad" : "unidades"} sin contrato`,
          },
        ]
      : []),
    {
      href: "/properties",
      icon: <Building2 />,
      title: "Ver tu inmueble",
      detail: "Sus unidades y sus contratos",
    },
  ];

  return (
    <main className="mx-auto grid w-full max-w-sheet items-start gap-5 px-4 py-12 md:grid-cols-2 md:gap-x-12 md:px-8 md:py-18">
      <div className="flex flex-col gap-4">
        <span className="grid size-16 place-items-center rounded-full bg-positive-tint text-positive-ink">
          <Check aria-hidden className="size-8" />
        </span>
        {me && (
          <p className="text-body font-semibold text-foreground-soft">
            Listo, {me.name.split(" ")[0]}
          </p>
        )}
        <h1 className="text-title-onboarding leading-tight font-bold">
          {draft.property.name} ya está en Arrendi
        </h1>
        <p className="text-section text-muted-foreground">
          {units} {units === 1 ? "unidad" : "unidades"}
          {outcome.leaseCreated && tenant ? ` y el contrato de ${tenant}` : ""}. Lo que sigue,
          cuando quieras:
        </p>
        {(outcome.documentFailed || outcome.inventoryFailed) && (
          <FormMessage tone="error">
            No pudimos subir{" "}
            {outcome.documentFailed && outcome.inventoryFailed
              ? "el contrato firmado ni el inventario"
              : outcome.documentFailed
                ? "el documento del contrato"
                : "el inventario"}
            . Puedes subirlo después, desde el contrato.
          </FormMessage>
        )}
      </div>
      <nav
        aria-label="Siguientes pasos"
        className="overflow-hidden rounded-xl border border-border bg-card md:col-start-2 md:row-span-2 md:row-start-1"
      >
        <ul>
          {steps.map((step) => (
            <li key={step.title} className="border-t border-border first:border-t-0">
              <Link
                href={step.href}
                onClick={markOnboarded}
                className="grid min-h-16 grid-cols-[2.5rem_minmax(0,1fr)_1.25rem] items-center gap-3 px-4 py-3 outline-none hover:bg-muted focus-visible:bg-muted [&_svg]:size-5"
              >
                <span aria-hidden className="grid size-10 place-items-center rounded-lg bg-muted">
                  {step.icon}
                </span>
                <span className="flex min-w-0 flex-col">
                  <span className="text-section font-semibold">{step.title}</span>
                  <span className="text-support text-muted-foreground">{step.detail}</span>
                </span>
                <ChevronRight aria-hidden className="text-muted-foreground" />
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <div className="md:col-start-1">
        <Button
          className="w-full md:w-auto"
          onClick={() => {
            markOnboarded();
            router.replace("/");
          }}
        >
          Ir al resumen
        </Button>
      </div>
    </main>
  );
}
