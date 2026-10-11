import type { Metadata } from "next";

import { PropertyStep } from "@/components/onboarding/PropertyStep";

export const metadata: Metadata = { title: "Tu inmueble · Arrendi" };

export default function OnboardingPropertyStepPage() {
  return <PropertyStep />;
}
