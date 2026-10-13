"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FormMessage } from "@/components/FormMessage";
import { DocumentPicker } from "@/components/leases/DocumentPicker";
import {
  LeaseForm,
  leaseTenant,
  newLeaseTerms,
  type LeaseValues,
} from "@/components/leases/LeaseForm";
import { OnboardingScreen } from "@/components/onboarding/OnboardingScreen";
import { Button } from "@/components/ui/button";
import { uploadLeaseDocument } from "@/lib/api/documents";
import { errorMessage, hasCode } from "@/lib/api/errors";
import { useMarkOnboarded, useOnboard } from "@/lib/api/queries";

import { useOnboarding } from "./OnboardingContext";

const FORM_ID = "onboarding-lease";

export function LeaseStep() {
  const router = useRouter();
  const { draft } = useOnboarding();
  const onboard = useOnboard();
  const markOnboarded = useMarkOnboarded();
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
    markOnboarded();
    router.replace("/");
  }

  /** Creates the property, its units and, if the owner filled it in, the first lease. */
  async function finish(values?: LeaseValues) {
    if (!property || !units) return;
    setSaving(true);
    setError(undefined);
    let created;
    try {
      created = await onboard.mutateAsync({
        body: {
          property,
          units,
          lease: values && {
            ...newLeaseTerms(values),
            auto_send: true,
            unit_index: Number(values.unit),
            tenant: leaseTenant(values),
          },
        },
      });
    } catch (problem) {
      // A second tap, or another tab, already did it.
      if (hasCode(problem, "onboarding_already_complete")) return goHome();
      setError(errorMessage(problem));
      setSaving(false);
      return;
    }
    if (created.lease && file && (await uploadLeaseDocument(created.lease.id, file))) {
      setDocumentFailed(true);
      setSaving(false);
      return;
    }
    goHome();
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
