import { currentEnvironment, ENVIRONMENTS } from "@/lib/environment";
import { cn } from "@/lib/utils";

// Written out whole so Tailwind finds the classes.
const TONES = {
  // Navy on the amber in both themes (AA contrast; white would not reach it).
  warning: "bg-warning text-rail",
  // White on the light theme's blue; navy on the dark theme's lighter one (AA contrast).
  info: "bg-info text-white dark:text-rail",
} as const;

// Behind the status bar of the installed app, whose time and battery are always white:
// the strong color of each tone, so they stay readable on the light theme too.
const STATUS_BAR = {
  warning: "bg-warning",
  info: "bg-info",
} as const;

/**
 * A strip across the top that says which environment this is. Never in production.
 *
 * On an iPhone, the app added to the home screen blurs whatever sits right under the
 * status bar. Outside production the app draws under the status bar (app/layout.tsx), so
 * the strip paints that area and its label starts below it, where nothing is blurred.
 */
export function EnvironmentBanner() {
  if (currentEnvironment === "production") return null;
  const { label, tone } = ENVIRONMENTS[currentEnvironment];
  return (
    <div role="status">
      <div aria-hidden className={cn("h-[env(safe-area-inset-top)]", STATUS_BAR[tone])} />
      <div
        className={cn(
          "flex h-6 items-center justify-center text-badge font-semibold tracking-wide uppercase",
          TONES[tone],
        )}
      >
        {label}
      </div>
    </div>
  );
}
