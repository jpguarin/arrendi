"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FormMessage } from "@/components/FormMessage";
import { Header } from "@/components/Header";
import { LoadError, Loading } from "@/components/LoadState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/api/errors";
import { useMe, useRemindBill, useSummary } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import {
  daysBetween,
  formatBillNumber,
  formatDayMonth,
  formatMonth,
  formatPesos,
  todayInBogota,
} from "@/lib/format";
import { BILL_STATUS, PAYMENT_METHOD_LABELS } from "@/lib/labels";

type Summary = components["schemas"]["SummaryResponse"];
type Bill = components["schemas"]["BillSummary"];

/** The month at a glance: collected of expected, what is pending and who is behind. */
function SummaryCard({ summary }: { summary: Summary }) {
  const percent =
    summary.expected > 0 ? Math.round((summary.collected / summary.expected) * 100) : 0;

  return (
    // The one block that looks the same in both themes.
    <section
      aria-label="Resumen del mes"
      className="flex flex-col gap-4 rounded-xl bg-summary p-5 text-summary-foreground"
    >
      <div className="flex flex-col gap-0.5">
        <p className="text-support text-summary-foreground-soft">Recaudado este mes</p>
        <p className="text-figure leading-tight font-bold">{formatPesos(summary.collected)}</p>
        <p className="text-support text-summary-foreground-soft">
          de {formatPesos(summary.expected)} esperados
        </p>
      </div>
      <div
        role="img"
        aria-label={`${percent} % recaudado`}
        className="h-2 overflow-hidden rounded-full bg-summary-inner"
      >
        <div className="h-full rounded-full bg-summary-foreground" style={{ width: `${percent}%` }} />
      </div>
      <dl className="grid grid-cols-2 gap-2">
        <div className="flex flex-col gap-0.5 rounded-lg bg-summary-inner px-3 py-2.5">
          <dt className="text-badge font-normal text-summary-foreground-soft">Pendiente</dt>
          <dd className="text-body font-bold">{formatPesos(summary.pending)}</dd>
        </div>
        <div className="flex flex-col gap-0.5 rounded-lg bg-summary-inner px-3 py-2.5">
          <dt className="text-badge font-normal text-summary-foreground-soft">En mora</dt>
          <dd className="text-body font-bold">
            {summary.units_overdue} de {summary.units_total}{" "}
            {summary.units_total === 1 ? "unidad" : "unidades"}
          </dd>
        </div>
      </dl>
    </section>
  );
}

/** What matters about a bill that is still owed, next to its status. */
function owedDetail(bill: Bill, today: string): string {
  if (bill.status === "overdue") {
    const days = daysBetween(bill.due_date, today);
    return days === 1 ? "hace 1 día" : `hace ${days} días`;
  }
  if (bill.balance < bill.total) return `abonó ${formatPesos(bill.total - bill.balance)}`;
  return `vence el ${formatDayMonth(bill.due_date)}`;
}

function ReceivableCard({
  bill,
  today,
  reminding,
  onRemind,
}: {
  bill: Bill;
  today: string;
  reminding: boolean;
  onRemind: () => void;
}) {
  const status = BILL_STATUS[bill.status];
  const partly = bill.balance < bill.total;

  return (
    <li className="flex flex-col gap-3 rounded-xl border border-border bg-card p-3.5">
      <Link
        href={`/bills/${bill.id}`}
        className="flex items-center justify-between gap-2.5 rounded-md outline-none focus-visible:bg-muted"
      >
        <span className="flex min-w-0 flex-col gap-1">
          <span className="truncate text-section font-semibold">
            {bill.unit_name} · {bill.tenant_name}
          </span>
          <span className="flex items-center gap-2 text-support text-muted-foreground">
            <Badge tone={status.tone}>{status.label}</Badge>
            <span className="truncate">{owedDetail(bill, today)}</span>
          </span>
        </span>
        <span className="flex shrink-0 flex-col items-end">
          <span className="text-body font-bold">{formatPesos(bill.balance)}</span>
          {partly && <span className="text-badge font-normal text-muted-foreground">saldo</span>}
        </span>
      </Link>
      <div className={bill.status === "overdue" ? "grid grid-cols-2 gap-2" : "grid"}>
        {bill.status === "overdue" && (
          <Button variant="outline" size="sm" disabled={reminding} onClick={onRemind}>
            {reminding ? "Enviando…" : "Enviar recordatorio"}
          </Button>
        )}
        {/* Two taps to register a payment: this one, and "Guardar pago". */}
        <Button asChild size="sm">
          <Link href={`/bills/${bill.id}/payment?from=home`}>Registrar pago</Link>
        </Button>
      </div>
    </li>
  );
}

function PaidRow({ bill }: { bill: Bill }) {
  const when = [
    bill.last_payment_date && formatDayMonth(bill.last_payment_date),
    bill.last_payment_method && PAYMENT_METHOD_LABELS[bill.last_payment_method].toLowerCase(),
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <li className="border-t border-border first:border-t-0">
      <Link
        href={`/bills/${bill.id}`}
        className="flex min-h-16 items-center justify-between gap-2.5 py-2 outline-none focus-visible:bg-muted"
      >
        <span className="flex min-w-0 flex-col gap-1">
          <span className="truncate text-section font-semibold">
            {bill.unit_name} · {bill.tenant_name}
          </span>
          <span className="flex items-center gap-2 text-support text-muted-foreground">
            <Badge tone="positive">Pagada</Badge>
            <span className="truncate">{when}</span>
          </span>
        </span>
        <span className="shrink-0 text-section font-bold">{formatPesos(bill.total)}</span>
      </Link>
    </li>
  );
}

function MonthSummary({ summary }: { summary: Summary }) {
  const remind = useRemindBill();
  const [reminded, setReminded] = useState<string>();
  const today = todayInBogota();
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
      <SummaryCard summary={summary} />

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

      {nothingYet && (
        <div className="flex flex-col items-center gap-4 py-8 text-center">
          <div className="flex flex-col gap-1">
            <p className="text-title-back font-bold">Aún no hay cuentas este mes</p>
            <p className="text-section text-muted-foreground">
              Se generan solas el día de envío, o puedes generarlas desde cada contrato.
            </p>
          </div>
          <Button asChild variant="outline" size="md">
            <Link href="/properties">Ir a mis contratos</Link>
          </Button>
        </div>
      )}

      {summary.receivable.length > 0 && (
        <section aria-labelledby="receivable" className="flex flex-col gap-2">
          <h2 id="receivable" className="text-section font-semibold">
            Por cobrar
          </h2>
          <ul className="flex flex-col gap-2">
            {summary.receivable.map((bill) => (
              <ReceivableCard
                key={bill.id}
                bill={bill}
                today={today}
                reminding={remind.isPending && remind.variables?.params.path.bill_id === bill.id}
                onRemind={() => sendReminder(bill)}
              />
            ))}
          </ul>
        </section>
      )}

      {summary.paid.length > 0 && (
        <section aria-labelledby="paid" className="flex flex-col gap-2">
          <h2 id="paid" className="text-section font-semibold">
            Pagadas
          </h2>
          <ul className="flex flex-col rounded-xl border border-border bg-card px-3.5">
            {summary.paid.map((bill) => (
              <PaidRow key={bill.id} bill={bill} />
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

/** The home screen: how the month is going and who owes what. */
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
        title={summary ? formatMonth(summary.month) : "Inicio"}
        subtitle={me && !onboarding ? `Hola, ${me.name}` : undefined}
      />
      <main className="flex flex-1 flex-col gap-4 px-5 pt-2 pb-6">
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
