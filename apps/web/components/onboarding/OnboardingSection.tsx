import { Check } from "lucide-react";
import Link from "next/link";

import { cn } from "@/lib/utils";

export type SectionState = "open" | "done" | "waiting";

type OnboardingSectionProps = {
  step: 1 | 2 | 3;
  title: string;
  /** What the part asks for, while it is not done. */
  hint: string;
  /** What was confirmed, once it is done. */
  summary: string;
  state: SectionState;
  /** Where "Editar" goes: the route that opens this part. */
  href: string;
  children?: React.ReactNode;
};

/**
 * One part of the onboarding sheet. Open, it shows its form; done, it folds into a line
 * with what was confirmed and "Editar"; waiting, it only says what comes.
 */
export function OnboardingSection({
  step,
  title,
  hint,
  summary,
  state,
  href,
  children,
}: OnboardingSectionProps) {
  const titleId = `onboarding-section-${step}`;
  const heading = (
    <>
      <span
        aria-hidden
        className={cn(
          "grid size-9 shrink-0 place-items-center rounded-full font-heading text-section font-extrabold",
          state === "open" && "bg-primary text-primary-foreground",
          state === "done" && "bg-positive-tint text-positive-ink",
          state === "waiting" && "bg-muted text-muted-foreground",
        )}
      >
        {state === "done" ? <Check className="size-4.5" /> : step}
      </span>
      <span className="flex min-w-0 flex-col">
        <span
          id={titleId}
          className={cn(
            "font-heading text-title-back font-bold",
            state === "waiting" && "text-muted-foreground",
          )}
        >
          {title}
        </span>
        <span className="truncate text-support text-muted-foreground">
          {state === "done" ? summary : hint}
        </span>
      </span>
    </>
  );

  return (
    <section
      aria-labelledby={titleId}
      className={cn(
        "overflow-hidden rounded-xl border bg-card",
        state === "open" ? "border-input" : "border-border",
      )}
    >
      {state === "done" ? (
        <Link
          href={href}
          className="grid min-h-18 grid-cols-[2.25rem_minmax(0,1fr)_auto] items-center gap-3 p-4 outline-none hover:bg-muted focus-visible:bg-muted"
        >
          {heading}
          <span className="text-support font-semibold underline underline-offset-3">Editar</span>
        </Link>
      ) : (
        <div className="grid min-h-18 grid-cols-[2.25rem_minmax(0,1fr)] items-center gap-3 p-4">
          {heading}
        </div>
      )}
      {state === "open" && <div className="flex flex-col gap-5 px-4 pb-5 sm:pl-16">{children}</div>}
    </section>
  );
}
