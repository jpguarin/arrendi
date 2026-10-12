"use client";

import { Bell } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { BillRow, BillTable } from "@/components/bills/BillRow";
import { FormMessage } from "@/components/FormMessage";
import { Header } from "@/components/Header";
import { LoadError, Loading } from "@/components/LoadState";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/api/errors";
import { useBills, useMe, useRemindBill, useSummary } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { formatBillNumber, formatMonth, formatPesos } from "@/lib/format";
import { cn } from "@/lib/utils";

type Summary = components["schemas"]["SummaryResponse"];
type Bill = components["schemas"]["BillSummary"];

/** The month a bill belongs to (`2026-10`): its period, or when it is due if it is manual. */
const monthOf = (bill: Bill) => (bill.period ?? bill.due_date).slice(0, 7);
const percentOf = (part: number, whole: number) => (whole > 0 ? Math.round((part / whole) * 100) : 0);

/** The month in four figures: expected, collected, pending and units behind. */
function Figures({ summary }: { summary: Summary }) {
  const figures = [
    { label: "Esperado", value: formatPesos(summary.expected) },
    {
      label: "Recaudado este mes",
      value: formatPesos(summary.collected),
      detail: `${percentOf(summary.collected, summary.expected)} % · de ${formatPesos(summary.expected)} esperados`,
    },
    { label: "Pendiente", value: formatPesos(summary.pending) },
    {
      label: "En mora",
      value: `${summary.units_overdue} de ${summary.units_total} ${summary.units_total === 1 ? "unidad" : "unidades"}`,
    },
  ];

  return (
    <dl
      aria-label="Resumen del mes"
      className="grid grid-cols-2 overflow-hidden rounded-xl border border-border bg-card lg:grid-cols-4"
    >
      {figures.map((figure) => (
        // The negative margins hide the lines on the outer edge of the grid.
        <div
          key={figure.label}
          className="-mt-px -ml-px flex flex-col border-t border-l border-border px-4 py-3.5"
        >
          <dt className="text-badge font-medium text-muted-foreground">{figure.label}</dt>
          <dd className="font-heading text-kpi leading-tight font-extrabold tracking-tight">
            {figure.value}
          </dd>
          {figure.detail && (
            <dd className="text-badge font-medium text-muted-foreground">{figure.detail}</dd>
          )}
        </div>
      ))}
    </dl>
  );
}

/**
 * What became of each peso expected this month, as one bar. Every part is also in the
 * legend with its label and value, so nothing rests on color alone.
 */
function Composition({ summary }: { summary: Summary }) {
  const month = summary.month.slice(0, 7);
  const owed = (status: Bill["status"]) =>
    summary.receivable
      .filter((bill) => bill.status === status && monthOf(bill) === month)
      .reduce((total, bill) => total + bill.balance, 0);
  const parts = [
    { label: "Recaudado", value: summary.collected, fill: "bg-positive" },
    { label: "Saldo de abonos", value: owed("partial"), fill: "bg-warning" },
    { label: "Por vencer", value: owed("pending"), fill: "bg-info" },
    { label: "Vencido", value: owed("overdue"), fill: "bg-alert" },
  ];
  const whole = parts.reduce((total, part) => total + part.value, 0);
  const shown = parts.filter((part) => part.value > 0);

  return (
    <figure className="flex flex-col rounded-xl border border-border bg-card p-4">
      <figcaption>
        <p className="text-section font-semibold">Cómo va el mes</p>
        <p className="text-badge text-muted-foreground">
          Lo esperado, según el estado de cada cuenta
        </p>
      </figcaption>
      <div
        role="img"
        aria-label={parts.map((part) => `${part.label}: ${formatPesos(part.value)}`).join(", ")}
        className="mt-3.5 flex h-5.5 gap-0.5"
      >
        {shown.map((part) => (
          <span
            key={part.label}
            title={`${part.label} · ${formatPesos(part.value)} · ${percentOf(part.value, whole)} %`}
            style={{ flexGrow: part.value }}
            className={cn("min-w-1.5 basis-0 first:rounded-l last:rounded-r", part.fill)}
          />
        ))}
      </div>
      <ul className="mt-3.5 grid grid-cols-2 gap-x-4 gap-y-2.5 @min-[900px]:grid-cols-4">
        {parts.map((part) => (
          <li key={part.label} className="grid grid-cols-[0.625rem_1fr] items-center gap-x-2 text-support">
            <span aria-hidden className={cn("size-2.5 rounded-[3px]", part.fill)} />
            <span>{part.label}</span>
            <span className="col-start-2 text-section font-semibold">
              {formatPesos(part.value)}{" "}
              <span className="text-badge font-normal text-muted-foreground">
                {percentOf(part.value, whole)} %
              </span>
            </span>
          </li>
        ))}
      </ul>
    </figure>
  );
}

const MONTHS_SHOWN = 6;

/** Collected over expected in the latest months, from the bills themselves. */
function MonthlyChart() {
  const { data: bills } = useBills();
  if (!bills || bills.length === 0) return null;

  const byMonth = new Map<string, { expected: number; collected: number }>();
  for (const bill of bills) {
    const month = byMonth.get(monthOf(bill)) ?? { expected: 0, collected: 0 };
    month.expected += bill.total;
    month.collected += bill.total - bill.balance;
    byMonth.set(monthOf(bill), month);
  }
  const months = [...byMonth].sort(([a], [b]) => a.localeCompare(b)).slice(-MONTHS_SHOWN);
  const top = Math.max(...months.map(([, month]) => month.expected));
  const inMillions = (amount: number) => `${(amount / 1_000_000).toFixed(1).replace(".", ",")} M`;

  return (
    <figure className="flex flex-col rounded-xl border border-border bg-card p-4">
      <figcaption>
        <p className="text-section font-semibold">Recaudo por mes</p>
        <p className="text-badge text-muted-foreground">Recaudado sobre lo esperado</p>
      </figcaption>
      <ul className="mt-3.5 flex h-32 items-end gap-3 border-b border-border">
        {months.map(([month, { expected, collected }]) => (
          <li
            key={month}
            title={`${formatMonth(month)} · ${formatPesos(collected)} de ${formatPesos(expected)}`}
            className="flex h-full flex-1 flex-col items-center justify-end gap-1 text-badge font-semibold"
          >
            <span>{inMillions(collected)}</span>
            {/* The track is what was expected; the bar inside, what came in. */}
            <span
              className="relative w-7 shrink-0 overflow-hidden rounded-t bg-muted"
              style={{ height: `${top > 0 ? (expected / top) * 78 : 0}%` }}
            >
              <span
                className="absolute inset-x-0 bottom-0 rounded-t bg-chart-bar"
                style={{ height: `${percentOf(collected, expected)}%` }}
              />
            </span>
          </li>
        ))}
      </ul>
      <ul aria-hidden className="flex gap-3 pt-1.5 text-center text-badge text-muted-foreground">
        {months.map(([month]) => (
          <li key={month} className="flex-1">
            {formatMonth(month, "short").split(" ")[0].toLowerCase()}
          </li>
        ))}
      </ul>
    </figure>
  );
}

function MonthSummary({ summary }: { summary: Summary }) {
  const remind = useRemindBill();
  const [reminded, setReminded] = useState<string>();
  const nothingYet =
    summary.expected === 0 && summary.receivable.length === 0 && summary.paid.length === 0;

  function sendReminder(bill: Bill) {
    setReminded(undefined);
    remind.mutate(
      { params: { path: { bill_id: bill.id } } },
      { onSuccess: () => setReminded(`El recordatorio va en camino a ${bill.tenant_name}.`) },
    );
  }

  return (
    <>
      <Figures summary={summary} />

      {summary.previous_pending > 0 && (
        <p className="text-support text-muted-foreground">
          Además, te deben {formatPesos(summary.previous_pending)} de meses anteriores.
        </p>
      )}
      {summary.bounced.map((bounced) => (
        <FormMessage key={bounced.bill_id} tone="error">
          El correo de la cuenta {formatBillNumber(bounced.number)} no llegó a {bounced.recipient}.{" "}
          <Link href={`/bills/${bounced.bill_id}`} className="font-semibold underline">
            Revisar
          </Link>
        </FormMessage>
      ))}
      {remind.error && <FormMessage tone="error">{errorMessage(remind.error)}</FormMessage>}
      {reminded && <FormMessage tone="success">{reminded}</FormMessage>}

      {nothingYet ? (
        <div className="flex flex-col items-center gap-4 py-8 text-center">
          <div className="flex flex-col gap-1">
            <p className="font-heading text-title-back font-extrabold">
              Aún no hay cuentas este mes
            </p>
            <p className="text-section text-muted-foreground">
              Se generan solas el día de envío, o puedes generarlas desde cada contrato.
            </p>
          </div>
          <Button asChild variant="outline" size="md">
            <Link href="/properties">Ir a mis contratos</Link>
          </Button>
        </div>
      ) : (
        <div className="grid gap-3 @min-[720px]:grid-cols-[1.6fr_1fr]">
          <Composition summary={summary} />
          <MonthlyChart />
        </div>
      )}

      {summary.receivable.length > 0 && (
        <section aria-labelledby="receivable" className="mt-2 flex flex-col gap-2.5">
          <div className="flex items-baseline justify-between gap-3">
            <h2 id="receivable" className="text-section font-semibold">
              Por cobrar
            </h2>
            <p className="text-support text-muted-foreground">Lo más urgente primero</p>
          </div>
          <BillTable amountLabel="Saldo" withActions>
            {summary.receivable.map((bill) => {
              const reminding =
                remind.isPending && remind.variables?.params.path.bill_id === bill.id;
              return (
                <BillRow
                  key={bill.id}
                  bill={bill}
                  actions={
                    <>
                      {bill.status === "overdue" && (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={reminding}
                          aria-label={`Enviar recordatorio a ${bill.tenant_name}`}
                          onClick={() => sendReminder(bill)}
                        >
                          <Bell aria-hidden className="size-4" />
                          <span className="@min-[600px]:sr-only">
                            {reminding ? "Enviando…" : "Recordar"}
                          </span>
                        </Button>
                      )}
                      {/* Two taps to register a payment: this one, and "Guardar pago". */}
                      <Button asChild size="sm">
                        <Link href={`/bills/${bill.id}/payment?from=home`}>Registrar pago</Link>
                      </Button>
                    </>
                  }
                />
              );
            })}
          </BillTable>
        </section>
      )}

      {summary.paid.length > 0 && (
        <section aria-labelledby="paid" className="mt-2 flex flex-col gap-2.5">
          <div className="flex items-center justify-between gap-3">
            <h2 id="paid" className="text-section font-semibold">
              Pagadas
            </h2>
            <Button asChild variant="outline" size="sm">
              <Link href="/bills">Ver todas</Link>
            </Button>
          </div>
          <BillTable>
            {summary.paid.map((bill) => (
              <BillRow key={bill.id} bill={bill} />
            ))}
          </BillTable>
        </section>
      )}
    </>
  );
}

/** The summary: how the month is going and who owes what. */
export function HomeScreen() {
  const router = useRouter();
  const { data: me } = useMe();
  // Nothing to show yet: the owner starts by creating their first property.
  const onboarding = me?.onboarding_complete === false;
  const { data: summary, error, refetch } = useSummary();

  useEffect(() => {
    if (onboarding) router.replace("/onboarding/property");
  }, [onboarding, router]);

  return (
    <>
      <Header
        title={summary ? formatMonth(summary.month) : "Resumen"}
        subtitle={me && !onboarding ? `Hola, ${me.name}` : undefined}
      />
      <main className="@container flex flex-1 flex-col gap-3 px-4 pb-8 md:px-6 xl:px-8">
        {onboarding ? (
          <Loading label="Abriendo el alta" />
        ) : summary ? (
          <MonthSummary summary={summary} />
        ) : error ? (
          <LoadError message={errorMessage(error)} onRetry={refetch} />
        ) : (
          <Loading label="Cargando el resumen del mes" />
        )}
      </main>
    </>
  );
}
