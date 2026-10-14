import { currentEnvironment, ENVIRONMENTS } from "@/lib/environment";
import { cn } from "@/lib/utils";

// Written out whole so Tailwind finds the classes.
const TONES = {
  // Navy on the amber in both themes (AA contrast; white would not reach it).
  warning: "bg-warning text-rail",
  // White on the light theme's blue; navy on the dark theme's lighter one (AA contrast).
  info: "bg-info text-white dark:text-rail",
} as const;

/**
 * A strip across the top that says which environment this is. Never in production.
 *
 * On an iPhone, iOS 26 blurs the top of the app opened from the home screen, a little
 * below the status bar, and there is no way to turn it off. There the strip grows upward
 * so its color fills the blurred band and the label sits below it, sharp.
 */
export function EnvironmentBanner() {
  if (currentEnvironment === "production") return null;
  const { label, tone } = ENVIRONMENTS[currentEnvironment];
  return (
    <div
      role="status"
      className={cn(
        "box-content flex h-6 items-center justify-center text-badge font-semibold tracking-wide uppercase standalone:pt-8",
        TONES[tone],
      )}
    >
      {label}
    </div>
  );
}
