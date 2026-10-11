"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { FormScreen, FormScreenFallback } from "@/components/FormScreen";
import { DocumentPicker } from "@/components/leases/DocumentPicker";
import { LeaseForm, leaseTerms, type LeaseValues } from "@/components/leases/LeaseForm";
import { LoadError, Loading } from "@/components/LoadState";
import { api } from "@/lib/api/client";
import { uploadLeaseDocument } from "@/lib/api/documents";
import { useLoad } from "@/lib/api/useLoad";
import { useSave } from "@/lib/api/useSave";

const FORM_ID = "lease";

export function NewLeaseScreen({ unitId }: { unitId: string | undefined }) {
  const router = useRouter();
  const { save, saving, error } = useSave();
  const [file, setFile] = useState<File | null>(null);
  // The API has no route for one unit; the list is short.
  const load = useCallback(() => api.GET("/api/properties"), []);
  const { data: properties, error: loadError, reload } = useLoad(load);
  const property = properties?.find((candidate) =>
    candidate.units.some((unit) => unit.id === unitId),
  );
  const unit = property?.units.find((candidate) => candidate.id === unitId);
  const activeLeaseId = unit?.active_lease?.id;

  // The unit is already rented (an old link, the back button): show that lease instead.
  useEffect(() => {
    if (activeLeaseId) router.replace(`/leases/${activeLeaseId}`);
  }, [activeLeaseId, router]);

  if (!property || !unit || activeLeaseId) {
    return (
      <FormScreenFallback title="Nuevo contrato" backHref="/properties">
        {loadError ? (
          <LoadError message={loadError} onRetry={reload} />
        ) : properties && !activeLeaseId ? (
          <LoadError message="No encontramos esta unidad." onRetry={reload} />
        ) : (
          <Loading label="Cargando la unidad" />
        )}
      </FormScreenFallback>
    );
  }

  async function onSubmit(values: LeaseValues) {
    const lease = await save(() =>
      api.POST("/api/leases", {
        body: {
          ...leaseTerms(values),
          auto_send: true,
          unit_id: unit!.id,
          tenant: { name: values.tenant_name, email: values.tenant_email },
        },
      }),
    );
    if (!lease) return;
    // The lease exists either way; if the document did not go up, its screen says so.
    const problem = file ? await uploadLeaseDocument(lease.id, file) : undefined;
    router.replace(`/leases/${lease.id}${problem ? "?document=failed" : ""}`);
    router.refresh();
  }

  return (
    <FormScreen
      title={`Nuevo contrato · ${unit.name}`}
      subtitle={property.name}
      backHref="/properties"
      formId={FORM_ID}
      submitLabel="Crear contrato"
      saving={saving}
      error={error}
    >
      <LeaseForm id={FORM_ID} showDeposit onSubmit={onSubmit}>
        <DocumentPicker file={file} onChange={setFile} />
      </LeaseForm>
    </FormScreen>
  );
}

export function EditLeaseScreen({ leaseId }: { leaseId: string }) {
  const router = useRouter();
  const back = `/leases/${leaseId}`;
  const { save, saving, error } = useSave();
  const load = useCallback(
    () => api.GET("/api/leases/{lease_id}", { params: { path: { lease_id: leaseId } } }),
    [leaseId],
  );
  const { data: lease, error: loadError, reload } = useLoad(load);

  if (!lease) {
    return (
      <FormScreenFallback title="Editar contrato" backHref={back}>
        {loadError ? (
          <LoadError message={loadError} onRetry={reload} />
        ) : (
          <Loading label="Cargando el contrato" />
        )}
      </FormScreenFallback>
    );
  }

  async function onSubmit(values: LeaseValues) {
    const saved = await save(() =>
      api.PATCH("/api/leases/{lease_id}", {
        params: { path: { lease_id: leaseId } },
        body: {
          ...leaseTerms(values),
          tenant: { name: values.tenant_name, email: values.tenant_email },
        },
      }),
    );
    if (!saved) return;
    router.replace(back);
    router.refresh();
  }

  return (
    <FormScreen
      title={`Editar contrato · ${lease.unit.name}`}
      subtitle={lease.unit.property_name}
      backHref={back}
      formId={FORM_ID}
      submitLabel="Guardar cambios"
      saving={saving}
      error={error}
    >
      <LeaseForm
        id={FORM_ID}
        showDeposit
        defaultValues={{
          tenant_name: lease.tenant.name,
          tenant_email: lease.tenant.email,
          rent: lease.rent,
          due_day: String(lease.due_day),
          start_date: lease.start_date,
          end_date: lease.end_date ?? "",
          deposit: lease.deposit,
        }}
        onSubmit={onSubmit}
      />
    </FormScreen>
  );
}
