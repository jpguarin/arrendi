"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FormMessage } from "@/components/FormMessage";
import { DocumentPicker } from "@/components/leases/DocumentPicker";
import { LeaseForm, leaseTerms, type LeaseValues } from "@/components/leases/LeaseForm";
import { OnboardingScreen } from "@/components/onboarding/OnboardingScreen";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import { uploadLeaseDocument } from "@/lib/api/documents";
import { apiErrorMessage, CONNECTION_ERROR } from "@/lib/api/errors";

import { useOnboarding } from "./OnboardingContext";

const FORM_ID = "onboarding-lease";

export function LeaseStep() {
  const router = useRouter();
  const { draft } = useOnboarding();
  const [file, setFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>();
  // Everything was created but the document did not go up: say so before moving on.
  const [documentFailed, setDocumentFailed] = useState(false);

  const { property, units } = draft;
  // The steps keep their answers in memory: after a reload there is nothing to build on.
  useEffect(() => {
    if (!property || !units) router.replace("/onboarding/property");
  }, [property, units, router]);
  if (!property || !units) return null;

  function goHome() {
    router.replace("/");
    router.refresh();
  }

  /** Creates the property, its units and, if the owner filled it in, the first lease. */
  async function finish(values?: LeaseValues) {
    if (!property || !units) return;
    setSaving(true);
    setError(undefined);
    try {
      const { data, error, response } = await api.POST("/api/onboarding", {
        body: {
          property,
          units,
          lease: values && {
            ...leaseTerms(values),
            auto_send: true,
            unit_index: Number(values.unit),
            tenant: { name: values.tenant_name, email: values.tenant_email },
          },
        },
      });
      // A second tap, or another tab, already did it.
      if (response.status === 409) return goHome();
      if (!data) {
        setError(apiErrorMessage(error));
        setSaving(false);
        return;
      }
      if (data.lease && file) {
        const problem = await uploadLeaseDocument(data.lease.id, file);
        if (problem) {
          setDocumentFailed(true);
          setSaving(false);
          return;
        }
      }
      goHome();
    } catch {
      setError(CONNECTION_ERROR);
      setSaving(false);
    }
  }

  if (documentFailed) {
    return (
      <OnboardingScreen
        step={3}
        title="Tu contrato quedó creado"
        description="Solo faltó el documento firmado."
        footer={<Button onClick={goHome}>Continuar</Button>}
      >
        <FormMessage tone="error">
          No pudimos subir el documento. Puedes subirlo después, desde el contrato.
        </FormMessage>
      </OnboardingScreen>
    );
  }

  return (
    <OnboardingScreen
      step={3}
      title="Tu primer contrato"
      description="Con estos datos generamos la cuenta de cobro cada mes."
      footer={
        <>
          <Button type="submit" form={FORM_ID} disabled={saving}>
            {saving ? "Guardando…" : "Crear contrato y terminar"}
          </Button>
          <Button variant="ghost" size="sm" disabled={saving} onClick={() => finish()}>
            Agregar los contratos después
          </Button>
        </>
      }
    >
      {error && <FormMessage tone="error">{error}</FormMessage>}
      <LeaseForm
        id={FORM_ID}
        units={units.map((unit, index) => ({ value: String(index), label: unit.name }))}
        defaultValues={draft.lease}
        onSubmit={finish}
      >
        <DocumentPicker file={file} onChange={setFile} />
      </LeaseForm>
    </OnboardingScreen>
  );
}
