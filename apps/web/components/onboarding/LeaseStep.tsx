"use client";

import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";

import { FormMessage } from "@/components/FormMessage";
import { DocumentPicker } from "@/components/leases/DocumentPicker";
import {
  LeaseForm,
  leaseTenant,
  newLeaseTerms,
  type LeaseValues,
} from "@/components/leases/LeaseForm";
import { Switch } from "@/components/ui/switch";
import { uploadLeaseDocument } from "@/lib/api/documents";
import { errorMessage, hasCode } from "@/lib/api/errors";
import { useMarkOnboarded, useOnboard } from "@/lib/api/queries";

import { useOnboarding } from "./OnboardingContext";

/** The "Crear" buttons of the summary submit this form, with or without a lease. */
export const LEASE_FORM_ID = "onboarding-lease";

/** Third part of the sheet: the first lease, optional, and creating it all. */
export function LeaseStep() {
  const router = useRouter();
  const { draft, update, file, setFile, setCreating, finish } = useOnboarding();
  const onboard = useOnboard();
  const markOnboarded = useMarkOnboarded();
  const [error, setError] = useState<string>();
  const keepTyped = useCallback((lease: Partial<LeaseValues>) => update({ lease }), [update]);

  const { property, units } = draft;
  if (!property || !units) return null;

  /** Creates the property, its units and, if the owner filled it in, the first lease. */
  async function create(values?: LeaseValues) {
    if (!property || !units) return;
    setCreating(true);
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
      setCreating(false);
      // A second tap, or another tab, already did it.
      if (hasCode(problem, "onboarding_already_complete")) {
        markOnboarded();
        router.replace("/");
        return;
      }
      setError(errorMessage(problem));
      return;
    }
    // Everything is created by now; only the document can still fail, and the closing
    // screen says so.
    const documentFailed = Boolean(
      created.lease && file && (await uploadLeaseDocument(created.lease.id, file)),
    );
    finish({ leaseCreated: Boolean(created.lease), documentFailed });
    setCreating(false);
    router.replace("/onboarding/done");
  }

  return (
    <>
      <div className="flex items-center justify-between gap-4 rounded-lg bg-muted px-4 py-3.5">
        <label htmlFor="with-lease" className="flex min-w-0 flex-col gap-0.5">
          <span className="text-section font-semibold">Agregar el primer contrato ahora</span>
          <span className="text-support text-muted-foreground">
            Si no, lo agregas desde la unidad.
          </span>
        </label>
        <Switch
          id="with-lease"
          checked={draft.withLease}
          onCheckedChange={(withLease) => update({ withLease })}
        />
      </div>
      {error && <FormMessage tone="error">{error}</FormMessage>}
      {draft.withLease ? (
        <LeaseForm
          id={LEASE_FORM_ID}
          units={units.map((unit, index) => ({ value: String(index), label: unit.name }))}
          defaultValues={draft.lease}
          onValuesChange={keepTyped}
          onSubmit={create}
        >
          <DocumentPicker file={file} onChange={setFile} />
        </LeaseForm>
      ) : (
        <form
          id={LEASE_FORM_ID}
          onSubmit={(event) => {
            event.preventDefault();
            void create();
          }}
        />
      )}
    </>
  );
}
