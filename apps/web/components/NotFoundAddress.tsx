"use client";

import { usePathname } from "next/navigation";

/** The address that was not found, as it was typed, on a plate like the one of a house. */
export function NotFoundAddress() {
  const pathname = usePathname();
  return (
    <p className="flex max-w-full flex-col items-start gap-0.5 rounded-lg border bg-card px-3.5 py-2.5 shadow-xs">
      <span className="text-badge font-semibold text-muted-foreground">Dirección</span>
      <code className="max-w-full truncate font-mono text-section font-semibold">{pathname}</code>
    </p>
  );
}
