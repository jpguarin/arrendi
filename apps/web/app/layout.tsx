import type { Metadata, Viewport } from "next";
import { Inter, Red_Hat_Display } from "next/font/google";
import { PwaProvider } from "@/components/PwaProvider";
import { QueryProvider } from "@/components/QueryProvider";
import { ThemeProvider } from "@/components/ThemeProvider";
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

export const metadata: Metadata = {
  title: "Arrendi",
  description: "Genera tus cuentas de cobro cada mes, envíalas por correo y sabe quién te debe.",
  appleWebApp: { capable: true, title: "Arrendi", statusBarStyle: "default" },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: BACKGROUND_LIGHT },
    { media: "(prefers-color-scheme: dark)", color: BACKGROUND_DARK },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es-CO" className={`${inter.variable} ${redHatDisplay.variable} h-full antialiased`} suppressHydrationWarning>
      <body className="min-h-full font-sans">
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
