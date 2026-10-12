"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FormScreen, FormScreenFallback } from "@/components/FormScreen";
import { DocumentPicker } from "@/components/leases/DocumentPicker";
import {
  LeaseForm,
  leaseTenant,
  leaseTerms,
  type LeaseValues,
} from "@/components/leases/LeaseForm";
import { LoadError, Loading } from "@/components/LoadState";
import { uploadLeaseDocument } from "@/lib/api/documents";
import { TENANT_DOCUMENT_TYPE } from "@/lib/labels";
import { errorMessage } from "@/lib/api/errors";
import { useCreateLease, useLease, useProperties, useUpdateLease } from "@/lib/api/queries";

const FORM_ID = "lease";

export function NewLeaseScreen({ unitId }: { unitId: string | undefined }) {
  const router = useRouter();
  const create = useCreateLease();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  // The API has no route for one unit; the list is short and usually in memory.
  const { data: properties, error, refetch } = useProperties();
  const property = properties?.find((candidate) =>
    candidate.units.some((unit) => unit.id === unitId),
  );
  const unit = property?.units.find((candidate) => candidate.id === unitId);
  const activeLeaseId = unit?.active_lease?.id;
  // From the first tap: creating the lease puts it in memory as this unit's active one,
  // and that must not send the owner away before the document goes up.
  const leaving = create.isPending || create.isSuccess || uploading;

  // The unit is already rented (an old link, the back button): show that lease instead.
  useEffect(() => {
    if (activeLeaseId && !leaving) router.replace(`/leases/${activeLeaseId}`);
  }, [activeLeaseId, leaving, router]);

  if (!leaving && (!property || !unit || activeLeaseId)) {
    return (
      <FormScreenFallback title="Nuevo contrato" backHref="/properties">
        {properties && !activeLeaseId ? (
          <LoadError message="No encontramos esta unidad." onRetry={refetch} />
        ) : error && !properties ? (
          <LoadError message={errorMessage(error)} onRetry={refetch} />
        ) : (
          <Loading label="Cargando la unidad" />
        )}
      </FormScreenFallback>
    );
  }

  async function onSubmit(values: LeaseValues) {
    if (!unitId) return;
    let lease;
    try {
      lease = await create.mutateAsync({
        body: {
          ...leaseTerms(values),
          auto_send: true,
          unit_id: unitId,
          tenant: leaseTenant(values),
        },
      });
    } catch {
      return; // `create.error` has it, and the screen shows it.
    }
    // The lease exists either way; if the document did not go up, its screen says so.
    setUploading(true);
    const problem = file ? await uploadLeaseDocument(lease.id, file) : undefined;
    router.replace(`/leases/${lease.id}${problem ? "?document=failed" : ""}`);
  }

  return (
    <FormScreen
      title={`Nuevo contrato · ${unit?.name ?? ""}`}
      subtitle={property?.name}
      backHref="/properties"
      formId={FORM_ID}
      submitLabel="Crear contrato"
      // Still "saving" after it worked: the screen is leaving and must not send it twice.
      saving={leaving}
      error={create.error ? errorMessage(create.error) : undefined}
    >
      <LeaseForm
        id={FORM_ID}
        showDeposit
        showChargeDeposit
        showTenantDocument
        showPaymentDetails
        onSubmit={onSubmit}
      >
        <DocumentPicker file={file} onChange={setFile} />
      </LeaseForm>
    </FormScreen>
  );
}

export function EditLeaseScreen({ leaseId }: { leaseId: string }) {
  const router = useRouter();
  const back = `/leases/${leaseId}`;
  const update = useUpdateLease();
  const { data: lease, error, refetch } = useLease(leaseId);

  if (!lease) {
    return (
      <FormScreenFallback title="Editar contrato" backHref={back}>
        {error ? (
          <LoadError message={errorMessage(error)} onRetry={refetch} />
        ) : (
          <Loading label="Cargando el contrato" />
        )}
      </FormScreenFallback>
    );
  }

  return (
    <FormScreen
      title={`Editar contrato · ${lease.unit.name}`}
      subtitle={lease.unit.property_name}
      backHref={back}
      formId={FORM_ID}
      submitLabel="Guardar cambios"
      saving={update.isPending || update.isSuccess}
      error={update.error ? errorMessage(update.error) : undefined}
    >
      <LeaseForm
        id={FORM_ID}
        showDeposit
        // Only the first monthly bill charges the deposit; once it is out, there is nothing to choose.
        showChargeDeposit={
          !lease.recent_bills.some((bill) => bill.origin === "monthly" && bill.status !== "voided")
        }
        showTenantDocument
        showPaymentDetails
        defaultValues={{
          tenant_name: lease.tenant.name,
          tenant_email: lease.tenant.email,
          // Without a number saved, the type was never really chosen.
          tenant_document_type: lease.tenant.document_number
            ? lease.tenant.document_type
            : TENANT_DOCUMENT_TYPE,
          tenant_document_number: lease.tenant.document_number ?? "",
          rent: lease.rent,
          due_day: String(lease.due_day),
          start_date: lease.start_date,
          end_date: lease.end_date ?? "",
          deposit: lease.deposit,
          charge_deposit: lease.charge_deposit,
          payment_details: lease.payment_details ?? "",
        }}
        onSubmit={(values: LeaseValues) =>
          update.mutate(
            {
              params: { path: { lease_id: leaseId } },
              body: {
                ...leaseTerms(values),
                tenant: leaseTenant(values),
              },
            },
            { onSuccess: () => router.replace(back) },
          )
        }
      />
    </FormScreen>
  );
}
