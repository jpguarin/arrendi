import type { Metadata } from "next";

import { OnboardingSheet } from "@/components/onboarding/OnboardingSheet";

export const metadata: Metadata = { title: "Tu primer contrato · Arrendi" };

export default function OnboardingLeasePage() {
  return <OnboardingSheet open="lease" />;
}
