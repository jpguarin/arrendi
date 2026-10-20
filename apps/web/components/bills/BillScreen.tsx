"use client";

import { Ban, Bell, Check, FilePlus2, type LucideIcon, Mail, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { ActionFooter } from "@/components/ActionFooter";
import { FormMessage } from "@/components/FormMessage";
import { Header } from "@/components/Header";
import { LoadError, Loading } from "@/components/LoadState";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { BillDocument } from "@/components/bills/BillDocument";
import { BillStatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import { openTemporaryLink } from "@/lib/api/documents";
import { errorMessage, hasCode } from "@/lib/api/errors";
import {
  useBill,
  useDeletePayment,
  useRemindBill,
  useRestoreLateFee,
  useSendBill,
  useVoidBill,
  useWaiveLateFee,
} from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import {
  formatBillNumber,
  formatDate,
  formatDateHour,
  formatMonth,
  formatPesos,
} from "@/lib/format";
import {
  DELIVERY_PROBLEMS,
  NOTIFICATION_LABELS,
  PAYMENT_METHOD_LABELS,
} from "@/lib/labels";
import { cn } from "@/lib/utils";

type Bill = components["schemas"]["BillResponse"];

const BACK = "/bills";
const PROOF_FAILED =
  "El pago quedó guardado, pero no pudimos subir el comprobante. Elimina el pago y regístralo de nuevo si lo necesitas.";

/** The bill as the tenant reads it. The stored PDF is the one that counts. */
function DocumentPreview({ bill }: { bill: Bill }) {
  return (
    <BillDocument
      number={bill.number}
      issueDate={bill.issue_date}
      // A monthly bill says its month and its unit under the rent, its first line. A manual
      // one has no line to say it under, so the unit goes in the heading.
      headingNote={bill.period ? null : bill.unit_name}
      issuer={bill.issuer}
      tenant={{
        name: bill.tenant_name,
        document_type: bill.tenant_document_type,
        document_number: bill.tenant_document_number,
      }}
      items={bill.items}
      ofTheRent={bill.period && `${formatMonth(bill.period)} · ${bill.unit_name}`}
      total={bill.total}
      dueDate={bill.due_date}
      lateFeeNotice={bill.late_fee?.notice}
      signed={bill.signed}
    />
  );
}

/** Where the late fee of the bill stands, and the owner's say on it while it is theirs. */
function LateFeeSection({
  bill,
  working,
  onWaive,
  onRestore,
}: {
  bill: Bill;
  working: boolean;
  onWaive: () => void;
  onRestore: () => void;
}) {
  const fee = bill.late_fee;
  // Nothing to say while the bill is in time: its preview already carries the warning.
  if (!fee || fee.status === "on_time") return null;
  const amount = formatPesos(fee.amount);

  return (
    <section
      aria-labelledby="late-fee"
      className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4"
    >
      <div className="flex flex-col gap-0.5">
        <h2 id="late-fee" className="text-section font-semibold">
          Recargo por mora
        </h2>
        <p className="text-support text-muted-foreground">
          {fee.status === "pending" &&
            `No quedó paga el ${formatDate(fee.deadline)}. La próxima cuenta del mes de este contrato cobrará ${amount}. Si el contrato termina antes, cóbralo con "Cobrar otro concepto".`}
          {fee.status === "waived" &&
            `Decidiste no cobrar el recargo de ${amount}. Ninguna cuenta lo incluirá.`}
          {fee.status === "charged" && `Se cobraron ${amount} en la `}
          {fee.status === "charged" && fee.charged_on && (
            <Link href={`/bills/${fee.charged_on.id}`} className="font-semibold underline">
              cuenta {formatBillNumber(fee.charged_on.number)}
            </Link>
          )}
          {fee.status === "charged" && "."}
        </p>
      </div>
      {fee.status === "pending" && (
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="outline" size="md" disabled={working}>
              No cobrar este recargo
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>¿No cobrar este recargo?</AlertDialogTitle>
              <AlertDialogDescription>
                La próxima cuenta del mes saldrá sin el recargo de {amount}. Puedes volver a
                cobrarlo mientras esa cuenta no se haya generado.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogAction onClick={onWaive}>No cobrarlo</AlertDialogAction>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
      {fee.status === "waived" && (
        <Button variant="outline" size="md" disabled={working} onClick={onRestore}>
          Volver a cobrarlo
        </Button>
      )}
    </section>
  );
}

type Tone = "positive" | "alert" | "neutral";
type Event = { key: string; at: string; Icon: LucideIcon; text: string; problem?: string; tone: Tone };

const EVENT_TONES: Record<Tone, string> = {
  positive: "bg-positive-tint text-positive-ink",
  alert: "bg-alert-tint text-alert-ink",
  neutral: "bg-muted text-foreground",
};

/** Everything that happened to the bill, oldest first: issued, emails, payments, voided. */
function history(bill: Bill): Event[] {
  const events: Event[] = [
    { key: "created", at: bill.created_at, Icon: FilePlus2, text: "Generada", tone: "neutral" },
  ];
  for (const notification of bill.notifications) {
    const failed =
      notification.delivery_status === "failed" || notification.delivery_status === "bounced";
    events.push({
      key: notification.id,
      at: notification.sent_at ?? notification.created_at,
      Icon: notification.type.includes("reminder") ? Bell : Mail,
      text: NOTIFICATION_LABELS[notification.type],
      problem: DELIVERY_PROBLEMS[notification.delivery_status],
      tone: failed ? "alert" : "neutral",
    });
  }
  for (const payment of bill.payments) {
    events.push({
      key: payment.id,
      at: payment.created_at,
      Icon: Check,
      // The hour is when it was written down; the day it was paid goes in the text.
      text: `Pago del ${formatDate(payment.payment_date)} registrado · ${formatPesos(payment.amount)} · ${PAYMENT_METHOD_LABELS[payment.method].toLowerCase()}`,
      tone: "positive",
    });
  }
  if (bill.voided_at) {
    events.push({ key: "voided", at: bill.voided_at, Icon: Ban, text: "Anulada", tone: "alert" });
  }
  return events.sort((a, b) => a.at.localeCompare(b.at));
}

/** The history of the bill as a timeline, each event with its date and hour. */
function History({ bill }: { bill: Bill }) {
  return (
    <section aria-labelledby="activity" className="flex flex-col gap-3">
      <h2 id="activity" className="text-section font-semibold">
        Historial
      </h2>
      <ol className="flex flex-col">
        {history(bill).map(({ key, at, Icon, text, problem, tone }) => (
          <li
            key={key}
            className="relative grid grid-cols-[1.75rem_minmax(0,1fr)] gap-3 pb-4 not-last:before:absolute not-last:before:top-8 not-last:before:bottom-0.5 not-last:before:left-3.25 not-last:before:w-0.5 not-last:before:rounded-full not-last:before:bg-border last:pb-0"
          >
            <span className={cn("grid size-7 place-items-center rounded-lg", EVENT_TONES[tone])}>
              <Icon aria-hidden strokeWidth={2.5} className="size-4" />
            </span>
            <div className="flex min-w-0 flex-col">
              <p className="text-section font-medium">
                {text}
                {problem && (
                  <span
                    className={cn(
                      "font-semibold",
                      tone === "alert" ? "text-alert-ink" : "text-muted-foreground",
                    )}
                  >
                    {" "}
                    · {problem}
                  </span>
                )}
              </p>
              <time dateTime={at} className="text-support text-muted-foreground">
                {formatDateHour(at)}
              </time>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

/** What has been paid on the bill, with the proof of each payment and a way to undo it. */
function PaymentsSection({
  bill,
  deleting,
  onDelete,
  onError,
}: {
  bill: Bill;
  deleting: boolean;
  onDelete: (paymentId: string) => void;
  onError: (message: string | undefined) => void;
}) {
  const [opening, setOpening] = useState<string>();

  async function openProof(paymentId: string) {
    setOpening(paymentId);
    onError(undefined);
    const problem = await openTemporaryLink(() =>
      api.GET("/api/payments/{payment_id}/proof", { params: { path: { payment_id: paymentId } } }),
    );
    setOpening(undefined);
    onError(problem);
  }

  return (
    <section aria-labelledby="payments" className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between gap-3">
        <h2 id="payments" className="text-section font-semibold">
          Pagos
        </h2>
        <p className="text-support text-muted-foreground">
          {bill.balance > 0 ? `Saldo ${formatPesos(bill.balance)}` : "Sin saldo"}
        </p>
      </div>
      <ul className="flex flex-col rounded-xl border border-border bg-card pr-1.5 pl-3.5">
        {bill.payments.map((payment) => (
          <li
            key={payment.id}
            className="flex min-h-16 items-center gap-2 border-t border-border py-2 first:border-t-0"
          >
            <div className="flex min-w-0 flex-1 flex-col gap-0.5">
              <p className="text-section font-semibold">{formatPesos(payment.amount)}</p>
              <p className="truncate text-support text-muted-foreground">
                {formatDate(payment.payment_date)} · {PAYMENT_METHOD_LABELS[payment.method]}
              </p>
            </div>
            {payment.has_proof && (
              <Button
                variant="ghost"
                size="sm"
                disabled={Boolean(opening)}
                onClick={() => openProof(payment.id)}
              >
                {opening === payment.id ? "Abriendo…" : "Comprobante"}
              </Button>
            )}
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-muted-foreground"
                  disabled={deleting}
                  aria-label={`Eliminar el pago de ${formatPesos(payment.amount)}`}
                >
                  <Trash2 aria-hidden className="size-4.5" />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>¿Eliminar este pago?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Se borra el pago de {formatPesos(payment.amount)} del{" "}
                    {formatDate(payment.payment_date)}
                    {payment.has_proof && ", con su comprobante"}, y la cuenta vuelve a deber ese
                    valor. Úsalo solo si lo registraste por error. No se puede deshacer.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogAction variant="destructive" onClick={() => onDelete(payment.id)}>
                    Eliminar pago
                  </AlertDialogAction>
                  <AlertDialogCancel>Cancelar</AlertDialogCancel>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function BillScreen({
  billId,
  proofFailed = false,
}: {
  billId: string;
  /** A payment was just saved, but its proof did not go up. */
  proofFailed?: boolean;
}) {
  const { data: bill, error: loadError, refetch } = useBill(billId);
  const voidBill = useVoidBill();
  const send = useSendBill();
  const remind = useRemindBill();
  const deletePayment = useDeletePayment();
  const waiveFee = useWaiveLateFee();
  const restoreFee = useRestoreLateFee();
  const [opening, setOpening] = useState(false);
  // What went wrong opening or uploading a file; the changes keep their own errors.
  const [pdfError, setPdfError] = useState<string | undefined>(
    proofFailed ? PROOF_FAILED : undefined,
  );
  // What the last email asked for was, until the next one.
  const [emailed, setEmailed] = useState<string>();

  if (!bill) {
    return (
      <>
        <Header title="Cuenta de cobro" backHref={BACK} />
        <main className="flex flex-1 flex-col gap-4 px-5 pt-2 pb-6">
          {hasCode(loadError, "not_found") ? (
            <FormMessage tone="error">No encontramos esta cuenta.</FormMessage>
          ) : loadError ? (
            <LoadError message={errorMessage(loadError)} onRetry={refetch} />
          ) : (
            <Loading label="Cargando la cuenta" />
          )}
        </main>
      </>
    );
  }

  // A bill with payments is not voided; neither is one already voided.
  const voidable =
    (bill.status === "pending" || bill.status === "overdue") && bill.payments.length === 0;
  const changeError =
    voidBill.error ??
    send.error ??
    remind.error ??
    deletePayment.error ??
    waiveFee.error ??
    restoreFee.error;
  const error = pdfError ?? (changeError ? errorMessage(changeError) : undefined);
  const path = { bill_id: billId };
  const voided = bill.status === "voided";
  // Whether the tenant has the bill: an email with it went out, or is on its way.
  const wasSent = bill.notifications.some(
    (notification) =>
      (notification.type === "bill" || notification.type === "resend") &&
      notification.delivery_status !== "failed",
  );
  const hasBalance = !voided && bill.status !== "paid";
  const emailing = send.isPending || remind.isPending;

  function sendBill() {
    setEmailed(undefined);
    send.mutate(
      { params: { path } },
      { onSuccess: () => setEmailed("La cuenta va en camino al correo del arrendatario.") },
    );
  }

  function sendReminder() {
    setEmailed(undefined);
    remind.mutate(
      { params: { path } },
      {
        onSuccess: () => setEmailed("El recordatorio va en camino al correo del arrendatario."),
      },
    );
  }

  async function openPdf() {
    setOpening(true);
    setPdfError(undefined);
    const problem = await openTemporaryLink(() =>
      api.GET("/api/bills/{bill_id}/pdf", { params: { path: { bill_id: billId } } }),
    );
    setOpening(false);
    setPdfError(problem);
  }

  return (
    <>
      <Header
        title={`Cuenta ${formatBillNumber(bill.number)}`}
        subtitle={`${bill.unit_name} · ${bill.tenant_name}`}
        backHref={BACK}
      >
        <BillStatusBadge status={bill.status} />
      </Header>
      <main className="flex flex-1 flex-col gap-4.5 px-5 pt-2 pb-6">
        {error && <FormMessage tone="error">{error}</FormMessage>}
        {!error && emailed && <FormMessage tone="success">{emailed}</FormMessage>}
        {!voided && !wasSent && !emailing && (
          <FormMessage tone="info">
            {bill.charges_late_fee
              ? "Esta cuenta trae un recargo por mora y no se envió sola. Revisa que el pago atrasado esté bien registrado antes de enviarla."
              : "Esta cuenta aún no se le ha enviado al arrendatario."}
          </FormMessage>
        )}
        {voided && (
          <FormMessage tone="info">
            Esta cuenta está anulada: ya no se cobra. Conserva su consecutivo y su PDF.
          </FormMessage>
        )}

        {!voided && (
          <section aria-label="Saldo" className="flex flex-col">
            <p className="text-support text-muted-foreground">
              {hasBalance ? "Saldo por cobrar" : "Total pagado"}
            </p>
            <p className="font-heading text-figure leading-tight font-extrabold tracking-tight">
              {formatPesos(hasBalance ? bill.balance : bill.total)}
            </p>
            <p className="text-support text-muted-foreground">
              {!hasBalance
                ? "Cuenta al día"
                : `${bill.status === "overdue" ? "Venció" : "Vence"} el ${formatDate(bill.due_date)}`}
              {hasBalance && bill.balance < bill.total &&
                ` · abonó ${formatPesos(bill.total - bill.balance)}`}
            </p>
          </section>
        )}

        <LateFeeSection
          bill={bill}
          working={waiveFee.isPending || restoreFee.isPending}
          onWaive={() => waiveFee.mutate({ params: { path } })}
          onRestore={() => restoreFee.mutate({ params: { path } })}
        />

        <DocumentPreview bill={bill} />

        {bill.payments.length > 0 && (
          <PaymentsSection
            bill={bill}
            deleting={deletePayment.isPending}
            onError={setPdfError}
            onDelete={(payment_id) => deletePayment.mutate({ params: { path: { payment_id } } })}
          />
        )}

        <History bill={bill} />
      </main>
      <ActionFooter>
        {hasBalance && (
          <Button asChild>
            <Link href={`/bills/${bill.id}/payment`}>Registrar pago</Link>
          </Button>
        )}
        {/* The rest, two to a row; an odd one out takes the whole row. */}
        <div className="grid grid-cols-2 gap-2 *:last:odd:col-span-2">
          {/* A bill that is already paid is not sent again. */}
          {!voided && !(wasSent && !hasBalance) && (
            <Button variant="outline" size="md" disabled={emailing} onClick={sendBill}>
              {send.isPending ? "Enviando…" : wasSent ? "Reenviar" : "Enviar"}
            </Button>
          )}
          {wasSent && hasBalance && (
            <Button variant="outline" size="md" disabled={emailing} onClick={sendReminder}>
              {remind.isPending ? "Enviando…" : "Recordar"}
            </Button>
          )}
          <Button variant="outline" size="md" disabled={opening} onClick={openPdf}>
            {opening ? "Abriendo…" : "Descargar PDF"}
          </Button>
          {voidable && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" size="md" disabled={voidBill.isPending}>
                  {voidBill.isPending ? "Anulando…" : "Anular"}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>¿Anular esta cuenta?</AlertDialogTitle>
                  <AlertDialogDescription>
                    La cuenta {formatBillNumber(bill.number)} deja de cobrarse. Conserva su
                    consecutivo y su PDF queda marcado como anulado. Si era la del mes, podrás
                    generar otra. Esta acción no se puede deshacer.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogAction
                    variant="destructive"
                    onClick={() => voidBill.mutate({ params: { path } })}
                  >
                    Anular cuenta
                  </AlertDialogAction>
                  <AlertDialogCancel>Cancelar</AlertDialogCancel>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>
      </ActionFooter>
    </>
  );
}
