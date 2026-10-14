import type { Metadata, Viewport } from "next";
import { Inter, Red_Hat_Display } from "next/font/google";
import { PwaProvider } from "@/components/PwaProvider";
import { QueryProvider } from "@/components/QueryProvider";
import { ThemeProvider } from "@/components/ThemeProvider";
import { EnvironmentBanner } from "@/components/EnvironmentBanner";
import { appIcons, currentEnvironment, ENVIRONMENTS, PRODUCTION_FAVICON } from "@/lib/environment";
import { BACKGROUND_DARK, BACKGROUND_LIGHT } from "@/lib/theme";
import "./globals.css";

// The brand fonts (docs/new-brand-design): Inter for the interface, Red Hat Display for
// titles and figures.
const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const redHatDisplay = Red_Hat_Display({
  variable: "--font-red-hat-display",
  subsets: ["latin"],
  weight: ["700", "800", "900"],
});

// Outside production the tab starts with the environment's emoji and has its own icon,
// to tell open tabs apart, and the app on the home screen is amber (lib/environment.ts).
// The pages' titles go through the template.
const environment = currentEnvironment === "production" ? null : ENVIRONMENTS[currentEnvironment];
const tabPrefix = environment ? `${environment.emoji} ` : "";

export const metadata: Metadata = {
  title: { default: `${tabPrefix}Arrendi`, template: `${tabPrefix}%s` },
  icons: {
    icon: environment?.favicon ?? PRODUCTION_FAVICON,
    apple: { url: appIcons.apple, sizes: "180x180", type: "image/png" },
  },
  description: "Genera tus cuentas de cobro cada mes, envíalas por correo y sabe quién te debe.",
  // An opaque status bar: with "black-translucent", iOS 26 blurs the top of the page and
  // the safe areas push the bottom bar up (docs/diseno.md).
  appleWebApp: { capable: true, title: "Arrendi", statusBarStyle: "default" },
};

export const viewport: Viewport = {
  // No zoom on a phone: the app behaves like an installed one, and a field does not
  // zoom the screen in when it takes focus.
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: BACKGROUND_LIGHT },
    { media: "(prefers-color-scheme: dark)", color: BACKGROUND_DARK },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es-CO" className={`${inter.variable} ${redHatDisplay.variable} h-full antialiased`} suppressHydrationWarning>
      <body className="min-h-full font-sans">
        <EnvironmentBanner />
        <ThemeProvider>
          <PwaProvider>
            <QueryProvider>
              {children}
            </QueryProvider>
          </PwaProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
