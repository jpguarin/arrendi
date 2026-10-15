import type { Metadata } from "next";

import { OnboardingSheet } from "@/components/onboarding/OnboardingSheet";

export const metadata: Metadata = { title: "Tu inmueble · Arrendi" };

export default function OnboardingPropertyPage() {
  return <OnboardingSheet open="property" />;
}
