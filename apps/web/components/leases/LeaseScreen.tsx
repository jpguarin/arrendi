"use client";

import { FileText, Pencil, Plus, Upload } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";

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
import { BillStatusBadge } from "@/components/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { api } from "@/lib/api/client";
import { DOCUMENT_TYPES, openTemporaryLink, uploadLeaseDocument } from "@/lib/api/documents";
import { errorMessage, hasCode } from "@/lib/api/errors";
import {
  useEndLease,
  useGenerateMonthlyBill,
  useLease,
  useRefreshLease,
  useSettings,
  useUpdateLease,
} from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import {
  formatBillNumber,
  formatDate,
  formatDateTime,
  formatDayMonth,
  formatMonth,
  formatPesos,
  todayInBogota,
} from "@/lib/format";
import { DOCUMENT_TYPE_LABELS } from "@/lib/labels";

type Lease = components["schemas"]["LeaseResponse"];

const BACK = "/properties";
const DOCUMENT_FAILED = "No pudimos subir el documento. Inténtalo de nuevo desde aquí.";

function Term({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-support text-muted-foreground">{label}</dt>
      <dd className="text-body font-semibold">{children}</dd>
    </div>
  );
}

/** The signed lease: open it, replace it, or upload it for the first time. */
function DocumentSection({
  lease,
  onChange,
  onError,
}: {
  lease: Lease;
  onChange: () => void;
  onError: (message: string | undefined) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<"uploading" | "opening">();

  async function upload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setBusy("uploading");
    onError(undefined);
    const problem = await uploadLeaseDocument(lease.id, file);
    setBusy(undefined);
    if (problem) onError(problem);
    else onChange();
  }

  async function open() {
    setBusy("opening");
    onError(undefined);
    const problem = await openTemporaryLink(() =>
      api.GET("/api/leases/{lease_id}/document", { params: { path: { lease_id: lease.id } } }),
    );
    setBusy(undefined);
    if (problem) onError(problem);
  }

  const picker = (
    <input
      ref={input}
      type="file"
      accept={DOCUMENT_TYPES.join(",")}
      className="sr-only"
      tabIndex={-1}
      aria-hidden
      onChange={upload}
    />
  );

  if (!lease.document_name) {
    return (
      <section aria-label="Documento del contrato" className="flex flex-col gap-2">
        {picker}
        <Button
          variant="dashed"
          size="md"
          disabled={Boolean(busy)}
          onClick={() => input.current?.click()}
        >
          <Upload aria-hidden />
          {busy === "uploading" ? "Subiendo…" : "Subir contrato firmado"}
        </Button>
      </section>
    );
  }

  return (
    <section
      aria-label="Documento del contrato"
      className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4"
    >
      {picker}
      <div className="flex items-center gap-3">
        <FileText aria-hidden className="size-5.5 shrink-0 text-primary" />
        <div className="flex min-w-0 flex-col gap-0.5">
          <p className="truncate text-section font-semibold">{lease.document_name}</p>
          {lease.document_uploaded_at && (
            <p className="text-support text-muted-foreground">
              Subido el {formatDateTime(lease.document_uploaded_at)}
            </p>
          )}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Button variant="outline" size="sm" disabled={Boolean(busy)} onClick={open}>
          {busy === "opening" ? "Abriendo…" : "Ver"}
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={Boolean(busy)}
          onClick={() => input.current?.click()}
        >
          {busy === "uploading" ? "Subiendo…" : "Reemplazar"}
        </Button>
      </div>
    </section>
  );
}

/** The latest bills of the lease, and the way to issue this month's by hand. */
function BillsSection({
  lease,
  generating,
  onGenerate,
}: {
  lease: Lease;
  generating: boolean;
  onGenerate: () => void;
}) {
  const period = `${todayInBogota().slice(0, 7)}-01`;
  const hasThisMonth = lease.recent_bills.some(
    (bill) => bill.period === period && bill.status !== "voided",
  );

  return (
    <section aria-labelledby="lease-bills" className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-3">
        <h2 id="lease-bills" className="text-section font-semibold">
          Cuentas de cobro
        </h2>
        {lease.recent_bills.length > 0 && (
          <Button asChild variant="link" size="sm" className="-mr-3">
            <Link href={`/bills?unit=${lease.unit.id}`}>Ver todas</Link>
          </Button>
        )}
      </div>
      {lease.recent_bills.length > 0 ? (
        <ul className="flex flex-col rounded-xl border border-border bg-card px-3.5">
          {lease.recent_bills.map((bill) => {
            return (
              <li key={bill.id} className="border-t border-border first:border-t-0">
                <Link
                  href={`/bills/${bill.id}`}
                  className="flex min-h-13 items-center justify-between gap-2.5 py-2 outline-none focus-visible:bg-muted"
                >
                  <span className="truncate text-section">
                    {bill.period
                      ? formatMonth(bill.period, "short")
                      : `Vence ${formatDayMonth(bill.due_date)}`}{" "}
                    · {formatBillNumber(bill.number)}
                  </span>
                  <span className="flex shrink-0 items-center gap-2.5">
                    <BillStatusBadge status={bill.status} />
                    <span className="text-section font-semibold">{formatPesos(bill.total)}</span>
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="text-support text-muted-foreground">
          Este contrato aún no tiene cuentas de cobro.
        </p>
      )}
      {lease.status === "active" && (
        <div className="flex flex-col gap-2 pt-1">
          {!hasThisMonth && (
            <Button variant="dashed" size="md" disabled={generating} onClick={onGenerate}>
              <Plus aria-hidden />
              {generating ? "Generando…" : `Generar cuenta de ${formatMonth(period).toLowerCase()}`}
            </Button>
          )}
          <Button asChild variant="outline" size="md">
            <Link href={`/bills/new?lease=${lease.id}`}>Cobrar otro concepto</Link>
          </Button>
        </div>
      )}
    </section>
  );
}

export function LeaseScreen({
  leaseId,
  documentFailed,
}: {
  leaseId: string;
  /** The lease was just created, but its document did not go up. */
  documentFailed: boolean;
}) {
  const { data: lease, error: loadError, refetch } = useLease(leaseId);
  const refresh = useRefreshLease(leaseId);
  const update = useUpdateLease();
  const end = useEndLease();
  const generate = useGenerateMonthlyBill();
  const { data: settings } = useSettings();
  // What went wrong with the document; the changes keep their own errors.
  const [documentError, setDocumentError] = useState<string | undefined>(
    documentFailed ? DOCUMENT_FAILED : undefined,
  );
  const changeError = update.error ?? end.error ?? generate.error;
  const error = documentError ?? (changeError ? errorMessage(changeError) : undefined);
  const working = update.isPending || end.isPending;

  if (!lease) {
    return (
      <>
        <Header title="Contrato" backHref={BACK} />
        <main className="flex flex-1 flex-col gap-4 px-5 pt-2 pb-6">
          {hasCode(loadError, "not_found") ? (
            <FormMessage tone="error">No encontramos este contrato.</FormMessage>
          ) : loadError ? (
            <LoadError message={errorMessage(loadError)} onRetry={refetch} />
          ) : (
            <Loading label="Cargando el contrato" />
          )}
        </main>
      </>
    );
  }

  const path = { lease_id: lease.id };
  const active = lease.status === "active";
  const pastEnd = active && lease.end_date !== null && lease.end_date < todayInBogota();

  return (
    <>
      <Header
        title={`Contrato · ${lease.unit.name}`}
        subtitle={lease.unit.property_name}
        backHref={BACK}
      >
        <Badge tone={active ? "positive" : "neutral"}>{active ? "Activo" : "Terminado"}</Badge>
      </Header>
      <main className="flex flex-1 flex-col gap-4 px-5 pt-2 pb-6">
        {error && <FormMessage tone="error">{error}</FormMessage>}
        {pastEnd && (
          <FormMessage tone="info">
            Este contrato pasó su fecha de fin. Sigue activo y generando cuentas hasta que lo
            termines.
          </FormMessage>
        )}

        <section
          aria-label="Arrendatario"
          className="flex flex-col gap-0.5 rounded-xl border border-border bg-card p-4"
        >
          <p className="text-support text-muted-foreground">Arrendatario</p>
          <p className="text-body font-semibold">{lease.tenant.name}</p>
          <p className="truncate text-section text-foreground-soft">{lease.tenant.email}</p>
          {lease.tenant.document_number && (
            <p className="text-support text-muted-foreground">
              {DOCUMENT_TYPE_LABELS[lease.tenant.document_type]} {lease.tenant.document_number}
            </p>
          )}
        </section>

        <dl className="grid grid-cols-2 gap-x-3 gap-y-4 rounded-xl border border-border bg-card p-4">
          <Term label="Canon mensual">{formatPesos(lease.rent)}</Term>
          <Term label="Día de pago">{lease.due_day} de cada mes</Term>
          <Term label="Inicio">{formatDate(lease.start_date)}</Term>
          <Term label="Fin">{lease.end_date ? formatDate(lease.end_date) : "Sin fecha"}</Term>
          <Term label="Depósito">
            {lease.deposit !== null ? formatPesos(lease.deposit) : "Sin depósito"}
          </Term>
        </dl>

        <DocumentSection
          lease={lease}
          onError={setDocumentError}
          onChange={refresh}
        />

        {lease.items.length > 0 && (
          <section
            aria-labelledby="lease-items"
            className="flex flex-col gap-2 rounded-xl border border-border bg-card p-4"
          >
            <h2 id="lease-items" className="text-support text-muted-foreground">
              Cada mes se cobra
            </h2>
            <ul className="flex flex-col gap-1.5 text-section">
              {[{ description: "Canon de arrendamiento", amount: lease.rent }, ...lease.items].map(
                (charged, index) => (
                  <li key={index} className="flex justify-between gap-3">
                    <span className="min-w-0 break-words">{charged.description}</span>
                    <span className="shrink-0 font-semibold">{formatPesos(charged.amount)}</span>
                  </li>
                ),
              )}
            </ul>
            <hr className="border-border" />
            <p className="flex items-baseline justify-between gap-3">
              <span className="text-section font-semibold">Total de cada mes</span>
              <span className="text-body font-bold">
                {formatPesos(lease.items.reduce((sum, charged) => sum + charged.amount, lease.rent))}
              </span>
            </p>
          </section>
        )}
        {lease.payment_details && (
          <section
            aria-labelledby="lease-payment-details"
            className="flex flex-col gap-0.5 rounded-xl border border-border bg-card p-4"
          >
            <h2 id="lease-payment-details" className="text-support text-muted-foreground">
              Datos de pago de este contrato
            </h2>
            <p className="text-section break-words whitespace-pre-line text-foreground-soft">
              {lease.payment_details}
            </p>
          </section>
        )}
        {active && settings && !settings.payment_details && !lease.payment_details && (
          <FormMessage tone="info">
            Tus cuentas saldrán sin datos de pago.{" "}
            <Link href="/settings" className="font-semibold underline">
              Agrégalos en Ajustes
            </Link>
            .
          </FormMessage>
        )}
        <BillsSection
          lease={lease}
          generating={generate.isPending}
          onGenerate={() => generate.mutate({ params: { path } })}
        />

        {active && (
          <label className="flex min-h-11 items-center justify-between gap-3 rounded-xl border border-border bg-card p-4">
            <span className="flex flex-col gap-0.5">
              <span className="text-body font-semibold">Enviar cuentas automáticamente</span>
              <span className="text-support text-muted-foreground">
                {settings && `Salen solas el día ${settings.send_day} de cada mes. `}
                Si lo apagas, cada cuenta espera a que tú la envíes.
              </span>
            </span>
            <Switch
              checked={lease.auto_send}
              disabled={working}
              onCheckedChange={(auto_send) =>
                update.mutate({ params: { path }, body: { auto_send } })
              }
            />
          </label>
        )}

        {/* The changes to the lease itself go last, after everything there is to read. */}
        <div className="flex flex-col gap-2 pt-2">
          <Button asChild size="md">
            <Link href={`/leases/${lease.id}/edit`}>
              <Pencil aria-hidden className="size-4" />
              Editar contrato
            </Link>
          </Button>
          <Button asChild variant="outline" size="md">
            <Link href={`/units/${lease.unit.id}/edit`}>
              <Pencil aria-hidden className="size-4" />
              Editar unidad
            </Link>
          </Button>
          {active && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" size="md" disabled={working}>
                  Terminar contrato
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>¿Terminar este contrato?</AlertDialogTitle>
                  <AlertDialogDescription>
                    {lease.unit.name} quedará vacía y dejará de generar cuentas de cobro. El
                    historial se conserva. Esta acción no se puede deshacer.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogAction
                    variant="destructive"
                    onClick={() => end.mutate({ params: { path } })}
                  >
                    Terminar contrato
                  </AlertDialogAction>
                  <AlertDialogCancel>Cancelar</AlertDialogCancel>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>
      </main>
    </>
  );
}
