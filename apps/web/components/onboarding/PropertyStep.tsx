"use client";

import { useRouter } from "next/navigation";
import { useCallback } from "react";

import { PropertyForm, type PropertyValues } from "@/components/properties/PropertyForm";
import { Button } from "@/components/ui/button";

import { useOnboarding } from "./OnboardingContext";

const FORM_ID = "onboarding-property";

/** First part of the sheet: the property. */
export function PropertyStep() {
  const router = useRouter();
  const { draft, update } = useOnboarding();
  const keepTyped = useCallback(
    (propertyInput: Partial<PropertyValues>) => update({ propertyInput }),
    [update],
  );

  return (
    <>
      <PropertyForm
        id={FORM_ID}
        defaultValues={draft.propertyInput ?? draft.property}
        onValuesChange={keepTyped}
        onSubmit={(property) => {
          update({ property, propertyInput: undefined });
          // Back from an edit, the units may already be confirmed: skip to what is missing.
          router.push(draft.units ? "/onboarding/lease" : "/onboarding/units");
        }}
      />
      <div>
        <Button type="submit" form={FORM_ID} size="md">
          Continuar
        </Button>
      </div>
    </>
  );
}
