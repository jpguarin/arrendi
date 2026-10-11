"use client";

import { useRouter } from "next/navigation";

import { OnboardingScreen } from "@/components/onboarding/OnboardingScreen";
import { PropertyForm } from "@/components/properties/PropertyForm";
import { Button } from "@/components/ui/button";

import { useOnboarding } from "./OnboardingContext";

const FORM_ID = "onboarding-property";

export function PropertyStep() {
  const router = useRouter();
  const { draft, update } = useOnboarding();

  return (
    <OnboardingScreen
      step={1}
      title="¿Qué inmueble arriendas?"
      description="Empieza con uno. Después puedes agregar más."
      footer={
        <Button type="submit" form={FORM_ID}>
          Continuar
        </Button>
      }
    >
      <PropertyForm
        id={FORM_ID}
        defaultValues={draft.property}
        onSubmit={(property) => {
          update({ property });
          router.push("/onboarding/units");
        }}
      />
    </OnboardingScreen>
  );
}
