import { ActionFooter } from "@/components/ActionFooter";
import { cn } from "@/lib/utils";

const STEPS = 3;

type OnboardingScreenProps = {
  step: 1 | 2 | 3;
  title: string;
  description: string;
  children: React.ReactNode;
  /** The actions of the step, fixed at the bottom. */
  footer: React.ReactNode;
};

/** Frame of an onboarding step: where the owner is, the question, and the action below. */
export function OnboardingScreen({
  step,
  title,
  description,
  children,
  footer,
}: OnboardingScreenProps) {
  const progress = `Paso ${step} de ${STEPS}`;

  return (
    <>
      <header className="flex flex-col gap-2.5 px-5 pt-7">
        <p className="text-support font-semibold text-primary">{progress}</p>
        <div role="img" aria-label={progress} className="flex gap-1.5">
          {Array.from({ length: STEPS }, (_, index) => (
            <div
              key={index}
              className={cn("h-1.5 flex-1 rounded-full", index < step ? "bg-primary" : "bg-input")}
            />
          ))}
        </div>
      </header>
      <main className="flex flex-1 flex-col gap-6 px-5 pt-7 pb-8">
        <div className="flex flex-col gap-2">
          <h1 className="text-title-onboarding leading-tight font-bold">{title}</h1>
          <p className="text-section text-muted-foreground">{description}</p>
        </div>
        {children}
      </main>
      <ActionFooter>{footer}</ActionFooter>
    </>
  );
}
