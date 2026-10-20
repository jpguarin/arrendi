import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ProfileScreen } from "@/components/onboarding/profile/ProfileScreen";
import { isProfileStep } from "@/components/onboarding/profile/steps";

export const metadata: Metadata = { title: "Tus datos · Arrendi" };

export default async function OnboardingProfileStepPage({
  params,
}: PageProps<"/onboarding/profile/[step]">) {
  const { step } = await params;
  if (!isProfileStep(step)) notFound();
  return <ProfileScreen step={step} />;
}
