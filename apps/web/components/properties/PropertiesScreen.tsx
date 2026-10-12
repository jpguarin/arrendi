"use client";

import { Pencil, Plus } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Header } from "@/components/Header";
import { LoadError, Loading } from "@/components/LoadState";
import { ListMain } from "@/components/shell/ListDetail";
import { TONE_BAR, UnitStatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import type { components } from "@/lib/api/schema";
import { errorMessage } from "@/lib/api/errors";
import { useProperties } from "@/lib/api/queries";
import { formatPesos } from "@/lib/format";
import { PROPERTY_TYPE_LABELS, UNIT_STATUS, UNIT_USE_LABELS } from "@/lib/labels";
import { cn } from "@/lib/utils";

type Property = components["schemas"]["PropertyResponse"];
type Unit = components["schemas"]["UnitResponse"];

// The columns of a wide table: unit, tenant, rent, status.
const COLUMNS =
  "@min-[600px]:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)_9rem_7.75rem] @min-[600px]:gap-x-3";

function UnitRow({ unit }: { unit: Unit }) {
  const pathname = usePathname();
  const lease = unit.active_lease;
  const open = lease ? pathname.startsWith(`/leases/${lease.id}`) : false;

  return (
    <li
      className={cn(
        "relative flex items-stretch border-t border-border before:absolute before:inset-y-2 before:left-0 before:w-[3px] before:rounded-r-full first:border-t-0",
        TONE_BAR[UNIT_STATUS[unit.status].tone],
      )}
    >
      {/* The whole row opens the lease, or starts one if the unit is vacant. */}
      <Link
        href={lease ? `/leases/${lease.id}` : `/leases/new?unit=${unit.id}`}
        aria-current={open ? "true" : undefined}
        className={cn(
          "grid min-h-14 min-w-0 flex-1 grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-0.5 py-2 pr-2 pl-4 outline-none hover:bg-muted focus-visible:bg-muted @min-[600px]:min-h-12",
          COLUMNS,
          open && "bg-accent hover:bg-accent",
        )}
      >
        <span className="truncate text-section font-semibold">
          {unit.name}{" "}
          <span className="font-normal text-muted-foreground">· {UNIT_USE_LABELS[unit.use]}</span>
        </span>
        <span className="hidden truncate text-section @min-[600px]:block">
          {lease ? lease.tenant_name : <span className="text-muted-foreground">Crear contrato</span>}
        </span>
        <span className="text-right text-section font-semibold whitespace-nowrap">
          {lease ? formatPesos(lease.rent) : "—"}
        </span>
        <span className="truncate text-support text-muted-foreground @min-[600px]:hidden">
          {lease ? lease.tenant_name : "Crear contrato"}
        </span>
        <span className="justify-self-end @min-[600px]:justify-self-start">
          <UnitStatusBadge status={unit.status} />
        </span>
      </Link>
      <Button asChild variant="ghost" size="icon" className="mr-1 shrink-0 self-center text-muted-foreground">
        <Link href={`/units/${unit.id}/edit`} aria-label={`Editar ${unit.name}`}>
          <Pencil aria-hidden className="size-4.5" />
        </Link>
      </Button>
    </li>
  );
}

function PropertyTable({ property }: { property: Property }) {
  const rented = property.units.filter((unit) => unit.active_lease);
  const totalRent = rented.reduce((sum, unit) => sum + (unit.active_lease?.rent ?? 0), 0);
  const place = [PROPERTY_TYPE_LABELS[property.type], property.address, property.city]
    .filter(Boolean)
    .join(" · ");

  return (
    <section aria-labelledby={`property-${property.id}`} className="flex flex-col gap-2.5">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <div className="flex min-w-0 flex-1 basis-60 flex-col">
          <h2
            id={`property-${property.id}`}
            className="truncate font-heading text-title-back font-extrabold"
          >
            {property.name}
          </h2>
          <p className="truncate text-support text-muted-foreground">{place}</p>
        </div>
        <div className="flex shrink-0 gap-1.5">
          <Button asChild variant="outline" size="sm">
            <Link href={`/properties/${property.id}/edit`} aria-label={`Editar ${property.name}`}>
              <Pencil aria-hidden className="size-4" />
              Editar
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link
              href={`/properties/${property.id}/units/new`}
              aria-label={`Agregar unidad a ${property.name}`}
            >
              <Plus aria-hidden className="size-4" />
              Unidad
            </Link>
          </Button>
        </div>
      </div>
      <div className="@container overflow-hidden rounded-xl border border-border bg-card">
        <div
          aria-hidden
          className={cn(
            "mr-12 hidden border-b border-border py-2.5 pr-2 pl-4 text-badge font-semibold text-muted-foreground @min-[600px]:grid",
            COLUMNS,
          )}
        >
          <span>Unidad</span>
          <span>Arrendatario</span>
          <span className="text-right">Canon</span>
          <span>Estado</span>
        </div>
        <ul>
          {property.units.map((unit) => (
            <UnitRow key={unit.id} unit={unit} />
          ))}
        </ul>
        <p className="border-t border-border bg-muted px-4 py-2.5 text-support text-muted-foreground">
          {rented.length} de {property.units.length} ocupadas · {formatPesos(totalRent)} al mes
        </p>
      </div>
    </section>
  );
}

export function PropertiesScreen() {
  const { data: properties, error, isPending, refetch } = useProperties();

  return (
    <>
      <Header title="Inmuebles">
        <Button asChild size="md">
          <Link href="/properties/new">
            <Plus aria-hidden />
            Agregar inmueble
          </Link>
        </Button>
      </Header>
      <ListMain className="gap-6">
        {/* With data in memory a failed refresh stays quiet: the list is still useful. */}
        {!properties && error && <LoadError message={errorMessage(error)} onRetry={refetch} />}
        {isPending && <Loading label="Cargando tus inmuebles" />}
        {properties?.length === 0 && (
          <div className="flex flex-1 flex-col items-center justify-center gap-4 py-10 text-center">
            <div className="flex flex-col gap-1">
              <p className="font-heading text-title-back font-extrabold">Aún no tienes inmuebles</p>
              <p className="text-section text-muted-foreground">
                Crea el primero para empezar a cobrar tus arriendos.
              </p>
            </div>
          </div>
        )}
        {properties?.map((property) => (
          <PropertyTable key={property.id} property={property} />
        ))}
        {properties && properties.length > 0 && (
          <p className="text-support text-muted-foreground">
            Una unidad sin contrato activo aparece como vacía y no genera cuentas de cobro.
          </p>
        )}
      </ListMain>
    </>
  );
}
