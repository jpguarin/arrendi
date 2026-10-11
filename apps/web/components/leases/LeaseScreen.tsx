"use client";

import { FileText, Upload } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";

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
import { Switch } from "@/components/ui/switch";
import { api } from "@/lib/api/client";
import { DOCUMENT_TYPES, uploadLeaseDocument } from "@/lib/api/documents";
import { apiErrorMessage, CONNECTION_ERROR, errorMessage, hasCode } from "@/lib/api/errors";
import { useEndLease, useLease, useRefreshLease, useUpdateLease } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { formatDate, formatDateTime, formatPesos, todayInBogota } from "@/lib/format";

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
    // Opened now, during the tap: a window opened after waiting for the API is blocked
    // as a pop-up, above all on iPhone.
    const tab = window.open("", "_blank");
    setBusy("opening");
    onError(undefined);
    try {
      const { data, error } = await api.GET("/api/leases/{lease_id}/document", {
        params: { path: { lease_id: lease.id } },
      });
      if (!data) {
        tab?.close();
        onError(apiErrorMessage(error));
      } else if (tab) tab.location.href = data.url;
      else window.location.assign(data.url);
    } catch {
      tab?.close();
      onError(CONNECTION_ERROR);
    }
    setBusy(undefined);
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
  // What went wrong with the document; the changes keep their own errors.
  const [documentError, setDocumentError] = useState<string | undefined>(
    documentFailed ? DOCUMENT_FAILED : undefined,
  );
  const changeError = update.error ?? end.error;
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

        {active && (
          <label className="flex min-h-11 items-center justify-between gap-3 rounded-xl border border-border bg-card p-4">
            <span className="flex flex-col gap-0.5">
              <span className="text-body font-semibold">Enviar cuentas automáticamente</span>
              <span className="text-support text-muted-foreground">
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
      </main>
      <ActionFooter>
        <div className={active ? "grid grid-cols-2 gap-2" : "grid"}>
          <Button asChild variant="outline" size="md">
            <Link href={`/leases/${lease.id}/edit`}>Editar contrato</Link>
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
      </ActionFooter>
    </>
  );
}
