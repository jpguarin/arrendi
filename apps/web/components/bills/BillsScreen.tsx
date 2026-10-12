"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { BillGroup, BillRow, BillTable } from "@/components/bills/BillRow";
import { Header } from "@/components/Header";
import { LoadError, Loading } from "@/components/LoadState";
import { ListMain } from "@/components/shell/ListDetail";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { errorMessage } from "@/lib/api/errors";
import { type BillFilters, useBills, useProperties } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { monthOf } from "@/lib/bills";
import { formatMonth, formatPesos } from "@/lib/format";

type Bill = components["schemas"]["BillSummary"];
type StatusFilter = NonNullable<BillFilters["status"]> | "all";

const ALL = "all";
// Provisional: voided bills stay out of "Todas" and have their own filter.
const STATUS_FILTERS: { value: StatusFilter; label: string }[] = [
  { value: ALL, label: "Todas" },
  { value: "receivable", label: "Por cobrar" },
  { value: "paid", label: "Pagadas" },
  { value: "voided", label: "Anuladas" },
];

/** The bills by month, in the order the API sends them: newest first. */
function byMonth(bills: Bill[]): [string, Bill[]][] {
  const months = new Map<string, Bill[]>();
  for (const bill of bills) {
    months.set(monthOf(bill), [...(months.get(monthOf(bill)) ?? []), bill]);
  }
  return [...months];
}

const sum = (bills: Bill[], amount: (bill: Bill) => number) =>
  bills.reduce((total, bill) => total + amount(bill), 0);

export function BillsScreen() {
  // A lease links here with its unit already chosen. The list stays on screen while
  // bills open and close next to it, so a new link has to move the filter too.
  const linkedUnit = useSearchParams().get("unit");
  const [seenLink, setSeenLink] = useState(linkedUnit);
  const [unitId, setUnitId] = useState(linkedUnit ?? ALL);
  if (linkedUnit !== seenLink) {
    setSeenLink(linkedUnit);
    if (linkedUnit) setUnitId(linkedUnit);
  }
  const [status, setStatus] = useState<StatusFilter>(ALL);
  const filtered = unitId !== ALL || status !== ALL;
  const {
    data: bills,
    error,
    isPending,
    refetch,
  } = useBills({
    unit_id: unitId === ALL ? undefined : unitId,
    status: status === ALL ? undefined : status,
  });
  const { data: properties } = useProperties();
  const units = properties?.flatMap((property) => property.units) ?? [];

  return (
    <>
      <Header title="Cuentas">
        <Button asChild size="md">
          <Link href="/bills/new" aria-label="Nueva cuenta de cobro">
            <Plus aria-hidden />
            Nueva cuenta
          </Link>
        </Button>
      </Header>
      <ListMain>
        {/* One row of filters; it scrolls sideways when it does not fit. */}
        <div className="-mx-4 flex items-center gap-2 overflow-x-auto px-4 py-0.5 [scrollbar-width:none] md:mx-0 md:px-0.5">
          <ToggleGroup
            type="single"
            aria-label="Filtrar por estado"
            className="flex shrink-0 gap-0 rounded-xl bg-muted p-1"
            value={status}
            // Tapping the selected filter again would clear it; keep it selected.
            onValueChange={(value) => value && setStatus(value as StatusFilter)}
          >
            {STATUS_FILTERS.map((filter) => (
              <ToggleGroupItem
                key={filter.value}
                value={filter.value}
                className="h-11 rounded-lg border-transparent bg-transparent px-3 text-support text-muted-foreground hover:bg-transparent hover:text-foreground data-[state=on]:border-transparent data-[state=on]:bg-card data-[state=on]:text-foreground data-[state=on]:shadow-xs"
              >
                {filter.label}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
          <Select value={unitId} onValueChange={setUnitId}>
            <SelectTrigger aria-label="Filtrar por unidad" className="h-11 w-auto shrink-0 gap-2 text-support font-semibold">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>Todas las unidades</SelectItem>
              {units.map((unit) => (
                <SelectItem key={unit.id} value={unit.id}>
                  {unit.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* With data in memory a failed refresh stays quiet: the list is still useful. */}
        {!bills && error && <LoadError message={errorMessage(error)} onRetry={refetch} />}
        {isPending && <Loading label="Cargando tus cuentas" />}

        {bills?.length === 0 &&
          (filtered ? (
            <p className="py-10 text-center text-section text-muted-foreground">
              No hay cuentas con estos filtros.
            </p>
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center gap-4 py-10 text-center">
              <div className="flex flex-col gap-1">
                <p className="font-heading text-title-back font-extrabold">
                  Aún no tienes cuentas de cobro
                </p>
                <p className="text-section text-muted-foreground">
                  Genera la cuenta del mes desde cada contrato, o crea un cobro aparte.
                </p>
              </div>
              <Button asChild size="md">
                <Link href="/properties">Ir a mis contratos</Link>
              </Button>
            </div>
          ))}

        {bills && bills.length > 0 && (
          <BillTable>
            {byMonth(bills).flatMap(([month, monthBills]) => [
              <BillGroup
                key={month}
                title={formatMonth(month)}
                // Collected of expected: the same figures the summary shows.
                detail={
                  status === "voided"
                    ? formatPesos(sum(monthBills, (bill) => bill.total))
                    : `${formatPesos(sum(monthBills, (bill) => bill.total - bill.balance))} de ${formatPesos(sum(monthBills, (bill) => bill.total))}`
                }
              />,
              ...monthBills.map((bill) => <BillRow key={bill.id} bill={bill} />),
            ])}
          </BillTable>
        )}
      </ListMain>
    </>
  );
}
