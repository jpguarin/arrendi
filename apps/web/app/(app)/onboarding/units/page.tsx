import type { Metadata } from "next";

import { OnboardingSheet } from "@/components/onboarding/OnboardingSheet";

export const metadata: Metadata = { title: "Tus unidades · Arrendi" };

export default function OnboardingUnitsPage() {
  return <OnboardingSheet open="units" />;
}
