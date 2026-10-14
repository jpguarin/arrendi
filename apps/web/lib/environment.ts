// Which environment this build of the web belongs to. next.config.ts sets
// NEXT_PUBLIC_APP_ENV from Vercel's VERCEL_ENV at build time; outside Vercel it is "local".
export type AppEnvironment = "production" | "preview" | "local";

export function appEnvironment(value: string | undefined): AppEnvironment {
  if (value === "production" || value === "preview") return value;
  // Vercel's "development" (vercel dev) is this computer too.
  return "local";
}

/** What marks each environment that is not production: the banner and the browser tab. */
export const ENVIRONMENTS = {
  preview: {
    label: "ENV · develop",
    emoji: "🧪",
    tone: "warning",
    favicon: "/icons/favicon-preview.png",
  },
  local: {
    label: "ENV · local",
    emoji: "💻",
    tone: "info",
    favicon: "/icons/favicon-local.png",
  },
} as const satisfies Record<Exclude<AppEnvironment, "production">, object>;

export const PRODUCTION_FAVICON = "/icons/favicon.png";

/** The icon of the app added to the home screen. Local and preview share the amber one. */
export const APP_ICONS = {
  production: {
    apple: "/icons/apple-icon.png",
    small: "/icons/icon-192.png",
    large: "/icons/icon-512.png",
  },
  test: {
    apple: "/icons/apple-icon-dev.png",
    small: "/icons/icon-dev-192.png",
    large: "/icons/icon-dev-512.png",
  },
} as const;

// Read by its full name so Next.js inlines it.
export const currentEnvironment = appEnvironment(process.env.NEXT_PUBLIC_APP_ENV);

export const appIcons = APP_ICONS[currentEnvironment === "production" ? "production" : "test"];
