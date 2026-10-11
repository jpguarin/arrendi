"use client";

import { Pencil, Plus } from "lucide-react";
import Link from "next/link";
import { useCallback } from "react";

import { Header } from "@/components/Header";
import { LoadError, Loading } from "@/components/LoadState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { useLoad } from "@/lib/api/useLoad";
import { formatPesos } from "@/lib/format";
import { UNIT_USE_LABELS } from "@/lib/labels";

type Property = components["schemas"]["PropertyResponse"];
type Unit = components["schemas"]["UnitResponse"];

// Until stage 5 a unit is only vacant or not; "En mora" and "Pago parcial" come with
// the bills.
const STATUS: Record<Unit["status"], { label: string; tone: "positive" | "neutral" }> = {
  up_to_date: { label: "Al día", tone: "positive" },
  vacant: { label: "Vacía", tone: "neutral" },
};

function UnitRow({ unit }: { unit: Unit }) {
  const lease = unit.active_lease;
  const status = STATUS[unit.status];

  return (
    <li className="flex items-center border-t border-border">
      {/* The whole row opens the lease, or starts one if the unit is vacant. */}
      <Link
        href={lease ? `/leases/${lease.id}` : `/leases/new?unit=${unit.id}`}
        className="flex min-h-17 min-w-0 flex-1 items-center justify-between gap-2.5 py-2 outline-none focus-visible:bg-muted"
      >
        <span className="flex min-w-0 flex-col gap-0.5">
          <span className="truncate text-section font-semibold">
            {unit.name} · {UNIT_USE_LABELS[unit.use]}
          </span>
          <span className="truncate text-support text-muted-foreground">
            {lease ? `${lease.tenant_name} · ${formatPesos(lease.rent)}` : "Crear contrato"}
          </span>
        </span>
        <Badge tone={status.tone}>{status.label}</Badge>
      </Link>
      <Button asChild variant="ghost" size="icon" className="-mr-2 ml-1 text-muted-foreground">
        <Link href={`/units/${unit.id}/edit`} aria-label={`Editar ${unit.name}`}>
          <Pencil aria-hidden className="size-4.5" />
        </Link>
      </Button>
    </li>
  );
}

function PropertyCard({ property }: { property: Property }) {
  const rented = property.units.filter((unit) => unit.active_lease);
  const totalRent = rented.reduce((sum, unit) => sum + (unit.active_lease?.rent ?? 0), 0);
  const place = [property.address, property.city].filter(Boolean).join(" · ");

  return (
    <>
      <section
        aria-labelledby={`property-${property.id}`}
        className="flex flex-col gap-3 rounded-xl border border-border bg-card px-3.5 pt-4 pb-1.5"
      >
        <div className="flex items-start justify-between gap-2.5">
          <div className="flex min-w-0 flex-col gap-0.5">
            <h2 id={`property-${property.id}`} className="truncate text-title-back font-bold">
              {property.name}
            </h2>
            {place && <p className="truncate text-support text-muted-foreground">{place}</p>}
          </div>
          <Button asChild variant="ghost" size="sm" className="-mt-2 -mr-2">
            <Link href={`/properties/${property.id}/edit`} aria-label={`Editar ${property.name}`}>
              Editar
            </Link>
          </Button>
        </div>
        <dl className="grid grid-cols-2 gap-2">
          <div className="flex flex-col gap-0.5 rounded-md bg-background px-2.5 py-2">
            <dt className="text-badge text-muted-foreground">Unidades</dt>
            <dd className="text-section font-semibold">
              {rented.length} de {property.units.length} ocupadas
            </dd>
          </div>
          <div className="flex flex-col gap-0.5 rounded-md bg-background px-2.5 py-2">
            <dt className="text-badge text-muted-foreground">Canon total</dt>
            <dd className="text-section font-semibold">{formatPesos(totalRent)} al mes</dd>
          </div>
        </dl>
        <ul>
          {property.units.map((unit) => (
            <UnitRow key={unit.id} unit={unit} />
          ))}
        </ul>
      </section>
      <Button asChild variant="dashed">
        <Link href={`/properties/${property.id}/units/new`}>
          <Plus aria-hidden />
          <span className="truncate">Agregar unidad a {property.name}</span>
        </Link>
      </Button>
    </>
  );
}

export function PropertiesScreen() {
  const load = useCallback(() => api.GET("/api/properties"), []);
  const { data: properties, error, reload } = useLoad(load);

  return (
    <>
      <Header title="Inmuebles">
        <Button asChild variant="outline" size="icon">
          <Link href="/properties/new" aria-label="Agregar inmueble">
            <Plus aria-hidden />
          </Link>
        </Button>
      </Header>
      <main className="flex flex-1 flex-col gap-4 px-5 pt-2 pb-6">
        {error && <LoadError message={error} onRetry={reload} />}
        {!error && !properties && <Loading label="Cargando tus inmuebles" />}
        {properties?.length === 0 && (
          <div className="flex flex-1 flex-col items-center justify-center gap-4 py-10 text-center">
            <div className="flex flex-col gap-1">
              <p className="text-title-back font-bold">Aún no tienes inmuebles</p>
              <p className="text-section text-muted-foreground">
                Crea el primero para empezar a cobrar tus arriendos.
              </p>
            </div>
            <Button asChild size="md">
              <Link href="/properties/new">
                <Plus aria-hidden />
                Agregar inmueble
              </Link>
            </Button>
          </div>
        )}
        {properties?.map((property) => (
          <PropertyCard key={property.id} property={property} />
        ))}
        {properties && properties.length > 0 && (
          <p className="text-support text-muted-foreground">
            Una unidad sin contrato activo aparece como vacía y no genera cuentas de cobro.
          </p>
        )}
      </main>
    </>
  );
}
