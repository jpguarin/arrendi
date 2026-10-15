import { Brand } from "@/components/Brand";
import { OnboardingProvider } from "@/components/onboarding/OnboardingContext";

// One provider for the whole sheet and its closing screen: it keeps what the owner filled
// in as they move between the parts.
export default function OnboardingLayout({ children }: LayoutProps<"/onboarding">) {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b border-border bg-card px-4 py-3.5 md:px-6 lg:px-8">
        <Brand className="h-6" />
      </header>
      <OnboardingProvider>{children}</OnboardingProvider>
    </div>
  );
}
