"use client";

import { Building2, FileText, House, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const TABS = [
  { href: "/", label: "Inicio", Icon: House },
  { href: "/bills", label: "Cuentas", Icon: FileText },
  { href: "/properties", label: "Inmuebles", Icon: Building2 },
  { href: "/settings", label: "Ajustes", Icon: SlidersHorizontal },
] as const;

function isCurrent(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

/** The main sections of the app, at the bottom of the screen. */
export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Principal"
      className="sticky bottom-0 mt-auto flex border-t border-border bg-card pb-[env(safe-area-inset-bottom)]"
    >
      {TABS.map(({ href, label, Icon }) => {
        const current = isCurrent(pathname, href);
        return (
          <Link
            key={href}
            href={href}
            aria-current={current ? "page" : undefined}
            className={cn(
              "flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 text-badge font-semibold outline-none focus-visible:bg-muted",
              current ? "text-primary" : "text-muted-foreground",
            )}
          >
            <Icon aria-hidden className="size-[22px]" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
