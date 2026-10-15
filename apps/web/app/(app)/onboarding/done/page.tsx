import type { Metadata } from "next";

import { OnboardingDone } from "@/components/onboarding/OnboardingDone";

export const metadata: Metadata = { title: "Listo · Arrendi" };

export default function OnboardingDonePage() {
  return <OnboardingDone />;
}
