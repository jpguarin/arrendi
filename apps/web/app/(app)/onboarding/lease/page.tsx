import type { Metadata } from "next";

import { LeaseStep } from "@/components/onboarding/LeaseStep";

export const metadata: Metadata = { title: "Tu primer contrato · Arrendi" };

export default function OnboardingLeaseStepPage() {
  return <LeaseStep />;
}
