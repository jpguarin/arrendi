import type { Metadata } from "next";

import { ProfileWelcome } from "@/components/onboarding/profile/ProfileWelcome";

export const metadata: Metadata = { title: "Tus datos · Arrendi" };

export default function OnboardingProfilePage() {
  return <ProfileWelcome />;
}
