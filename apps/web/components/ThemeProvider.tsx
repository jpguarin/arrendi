"use client";

import { ThemeProvider as NextThemesProvider, useTheme } from "next-themes";
import { useEffect } from "react";

import { BACKGROUND_DARK, BACKGROUND_LIGHT } from "@/lib/theme";

/** Keeps the system bar (`theme-color`) the same color as the app background. */
function SystemBarColor() {
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    if (!resolvedTheme) return;
    const background = resolvedTheme === "dark" ? BACKGROUND_DARK : BACKGROUND_LIGHT;
    // The layout renders one tag per system theme; the theme the owner chose wins.
    document
      .querySelectorAll('meta[name="theme-color"]')
      .forEach((meta) => meta.setAttribute("content", background));
  }, [resolvedTheme]);

  return null;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <SystemBarColor />
      {children}
    </NextThemesProvider>
  );
}
