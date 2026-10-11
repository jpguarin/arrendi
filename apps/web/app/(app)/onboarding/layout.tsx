import { OnboardingProvider } from "@/components/onboarding/OnboardingContext";

// One provider for the three steps: it keeps what the owner filled in as they move
// between them.
export default function OnboardingLayout({ children }: LayoutProps<"/onboarding">) {
  return <OnboardingProvider>{children}</OnboardingProvider>;
}
