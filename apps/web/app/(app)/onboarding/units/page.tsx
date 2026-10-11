import type { Metadata } from "next";

import { UnitsStep } from "@/components/onboarding/UnitsStep";

export const metadata: Metadata = { title: "Tus unidades · Arrendi" };

export default function OnboardingUnitsStepPage() {
  return <UnitsStep />;
}
