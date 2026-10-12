"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { BillRow } from "@/components/bills/BillRow";
import { Header } from "@/components/Header";
import { LoadError, Loading } from "@/components/LoadState";
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

/** The month a bill belongs to (`2026-10`): its period, or when it is due if it is manual. */
const monthOf = (bill: Bill) => (bill.period ?? bill.due_date).slice(0, 7);

/** The bills by month, in the order the API sends them: newest first. */
function byMonth(bills: Bill[]): [string, Bill[]][] {
  const months = new Map<string, Bill[]>();
  for (const bill of bills) {
    months.set(monthOf(bill), [...(months.get(monthOf(bill)) ?? []), bill]);
  }
  return [...months];
}

export function BillsScreen({ initialUnitId }: { initialUnitId?: string }) {
  const [unitId, setUnitId] = useState(initialUnitId ?? ALL);
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
      <Header title="Cuentas de cobro">
        <Button asChild size="icon">
          <Link href="/bills/new" aria-label="Nueva cuenta de cobro">
            <Plus aria-hidden />
          </Link>
        </Button>
      </Header>
      <main className="flex flex-1 flex-col gap-4 px-5 pt-2 pb-6">
        <div className="flex flex-col gap-2.5">
          <Select value={unitId} onValueChange={setUnitId}>
            <SelectTrigger aria-label="Filtrar por unidad">
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
          <ToggleGroup
            type="single"
            aria-label="Filtrar por estado"
            className="flex flex-wrap"
            value={status}
            // Tapping the selected filter again would clear it; keep it selected.
            onValueChange={(value) => value && setStatus(value as StatusFilter)}
          >
            {STATUS_FILTERS.map((filter) => (
              <ToggleGroupItem
                key={filter.value}
                value={filter.value}
                className="h-11 rounded-full px-3.5 text-section"
              >
                {filter.label}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
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
                <p className="text-title-back font-bold">Aún no tienes cuentas de cobro</p>
                <p className="text-section text-muted-foreground">
                  Genera la cuenta del mes desde cada contrato, o crea un cobro aparte.
                </p>
              </div>
              <Button asChild size="md">
                <Link href="/properties">Ir a mis contratos</Link>
              </Button>
            </div>
          ))}

        {bills &&
          byMonth(bills).map(([month, monthBills]) => (
            <section key={month} aria-labelledby={`month-${month}`} className="flex flex-col gap-2">
              <div className="flex items-baseline justify-between gap-3">
                <h2 id={`month-${month}`} className="text-section font-semibold">
                  {formatMonth(month)}
                </h2>
                {/* Collected of expected: the same figures the home screen shows. */}
                <p className="text-support text-muted-foreground">
                  {status === "voided"
                    ? formatPesos(monthBills.reduce((sum, bill) => sum + bill.total, 0))
                    : `${formatPesos(
                        monthBills.reduce((sum, bill) => sum + bill.total - bill.balance, 0),
                      )} de ${formatPesos(monthBills.reduce((sum, bill) => sum + bill.total, 0))}`}
                </p>
              </div>
              <ul className="flex flex-col rounded-xl border border-border bg-card px-3.5">
                {monthBills.map((bill) => (
                  <BillRow key={bill.id} bill={bill} />
                ))}
              </ul>
            </section>
          ))}
      </main>
    </>
  );
}
