import { currentEnvironment, ENVIRONMENTS } from "@/lib/environment";
import { cn } from "@/lib/utils";

// Written out whole so Tailwind finds the classes.
const TONES = {
  warning: "bg-warning-tint text-warning-ink",
  // White on the light theme's blue; navy on the dark theme's lighter one (AA contrast).
  info: "bg-info text-white dark:text-rail",
} as const;

/** A strip across the top that says which environment this is. Never in production. */
export function EnvironmentBanner() {
  if (currentEnvironment === "production") return null;
  const { label, tone } = ENVIRONMENTS[currentEnvironment];
  return (
    <div
      role="status"
      className={cn(
        "flex h-6 items-center justify-center text-badge font-semibold tracking-wide uppercase",
        TONES[tone],
      )}
    >
      {label}
    </div>
  );
}
