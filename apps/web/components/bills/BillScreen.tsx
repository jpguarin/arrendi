"use client";

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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import { openTemporaryLink } from "@/lib/api/documents";
import { errorMessage, hasCode } from "@/lib/api/errors";
import { useBill, useVoidBill } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import {
  formatBillNumber,
  formatDateTime,
  formatLongDate,
  formatMonth,
  formatPesos,
} from "@/lib/format";
import { BILL_STATUS } from "@/lib/labels";

type Bill = components["schemas"]["BillResponse"];

const BACK = "/bills";

const withDocument = (name: string, document: string | null) =>
  document ? `${name} · C.C./NIT ${document}` : name;

/** The bill as the tenant reads it. The stored PDF is the one that counts. */
function DocumentPreview({ bill }: { bill: Bill }) {
  const detail = bill.period ? `${formatMonth(bill.period)} · ${bill.unit_name}` : bill.unit_name;

  return (
    <section
      aria-label="Vista previa del documento"
      className="flex flex-col gap-3.5 rounded-md border border-border bg-card p-5"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-0.5">
          <p className="text-body font-bold">Cuenta de cobro</p>
          <p className="text-badge font-normal text-muted-foreground">
            {formatBillNumber(bill.number)} · {formatLongDate(bill.issue_date)}
          </p>
        </div>
        <p className="text-right text-badge font-normal text-muted-foreground">
          {bill.issuer.name}
          {bill.issuer.document_number && (
            <>
              <br />
              C.C./NIT {bill.issuer.document_number}
            </>
          )}
        </p>
      </div>
      <hr className="border-border" />
      <div className="flex flex-col gap-0.5">
        <p className="text-badge font-normal text-muted-foreground">Debe</p>
        <p className="text-section font-semibold">
          {withDocument(bill.tenant_name, bill.tenant_document_number)}
        </p>
      </div>
      {bill.items.map((item, index) => (
        <div key={index} className="flex justify-between gap-3 text-section">
          <p className="min-w-0 break-words">
            {item.description}
            <br />
            <span className="text-support text-muted-foreground">{detail}</span>
          </p>
          <p className="shrink-0 font-semibold">{formatPesos(item.amount)}</p>
        </div>
      ))}
      <hr className="border-border" />
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-section font-semibold">Total a pagar</p>
        <p className="text-title font-bold">{formatPesos(bill.total)}</p>
      </div>
      <p className="rounded-md bg-background px-3 py-2.5 text-support whitespace-pre-line text-foreground-soft">
        Vence el {formatLongDate(bill.due_date)}
        {bill.issuer.payment_details && `\nPagar a: ${bill.issuer.payment_details}`}
      </p>
    </section>
  );
}

export function BillScreen({ billId }: { billId: string }) {
  const { data: bill, error: loadError, refetch } = useBill(billId);
  const voidBill = useVoidBill();
  const [opening, setOpening] = useState(false);
  const [pdfError, setPdfError] = useState<string>();

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

  const status = BILL_STATUS[bill.status];
  // A bill with payments is not voided; neither is one already voided.
  const voidable = bill.status === "pending" || bill.status === "overdue";
  const error = pdfError ?? (voidBill.error ? errorMessage(voidBill.error) : undefined);

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
        <Badge tone={status.tone}>{status.label}</Badge>
      </Header>
      <main className="flex flex-1 flex-col gap-4.5 px-5 pt-2 pb-6">
        {error && <FormMessage tone="error">{error}</FormMessage>}
        {bill.status === "voided" && (
          <FormMessage tone="info">
            Esta cuenta está anulada: ya no se cobra. Conserva su consecutivo y su PDF.
          </FormMessage>
        )}

        <DocumentPreview bill={bill} />

        <section aria-labelledby="activity" className="flex flex-col gap-2.5">
          <h2 id="activity" className="text-section font-semibold">
            Actividad
          </h2>
          {/* Emails and payments join this list in stages 4 and 5. */}
          <ol className="flex flex-col gap-2.5 text-section">
            {bill.voided_at && (
              <li className="flex justify-between gap-3">
                <span>Anulada</span>
                <span className="text-muted-foreground">{formatDateTime(bill.voided_at)}</span>
              </li>
            )}
            <li className="flex justify-between gap-3">
              <span>Generada</span>
              <span className="text-muted-foreground">{formatDateTime(bill.created_at)}</span>
            </li>
          </ol>
        </section>
      </main>
      <ActionFooter>
        <div className={voidable ? "grid grid-cols-2 gap-2" : "grid"}>
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
                    onClick={() => voidBill.mutate({ params: { path: { bill_id: billId } } })}
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
