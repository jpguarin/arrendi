"use client";

import { Building2, FileText, House, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Brand, BrandMark } from "@/components/Brand";
import { cn } from "@/lib/utils";

// `under` are the paths that belong to a section without starting like its link.
const SECTIONS = [
  { href: "/", label: "Resumen", Icon: House, under: [] },
  { href: "/bills", label: "Cuentas", Icon: FileText, under: [] },
  { href: "/properties", label: "Inmuebles", Icon: Building2, under: ["/leases", "/units"] },
  { href: "/settings", label: "Ajustes", Icon: SlidersHorizontal, under: [] },
] as const;

const within = (pathname: string, href: string) =>
  href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);

/**
 * The frame of the signed-in screens: the sections on a rail at the left from tablet up,
 * and on a bar at the bottom on a phone.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  // On a phone a detail takes the whole screen, without the bar under it.
  const topLevel = SECTIONS.some((section) => section.href === pathname);

  return (
    <div className="flex min-h-dvh flex-col md:grid md:grid-cols-[4.25rem_minmax(0,1fr)]">
      <div className="flex min-w-0 flex-1 flex-col">
        {/* On a phone the brand heads each section; from tablet up it is on the rail. */}
        {topLevel && (
          <div className="flex h-13 items-center border-b border-border bg-card px-4 md:hidden">
            <Brand />
          </div>
        )}
        {children}
      </div>
      <nav
        aria-label="Principal"
        className={cn(
          "sticky bottom-0 z-20 flex bg-rail pb-[env(safe-area-inset-bottom)] text-rail-muted md:top-0 md:order-first md:h-dvh md:flex-col md:items-center md:gap-1 md:px-1.5 md:py-4",
          !topLevel && "max-md:hidden",
        )}
      >
        <Link
          href="/"
          aria-label="Arrendi, resumen"
          className="mb-4 hidden rounded-lg p-1 text-rail-foreground outline-none focus-visible:ring-3 focus-visible:ring-ring md:block"
        >
          <BrandMark className="h-7" />
        </Link>
        {SECTIONS.map(({ href, label, Icon, under }) => {
          const current = [href, ...under].some((path) => within(pathname, path));
          return (
            <Link
              key={href}
              href={href}
              aria-current={current ? "page" : undefined}
              className={cn(
                "relative flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 text-[0.6875rem] font-semibold outline-none hover:text-rail-foreground focus-visible:bg-rail-active md:w-full md:flex-none md:rounded-lg",
                // A green mark on the current section: above it on the bar, beside it on the rail.
                "before:absolute before:top-0 before:left-1/2 before:hidden before:h-[3px] before:w-7 before:-translate-x-1/2 before:rounded-b-full before:bg-brand-green md:before:top-1/2 md:before:-left-1.5 md:before:h-6 md:before:w-[3px] md:before:translate-x-0 md:before:-translate-y-1/2 md:before:rounded-r-full md:before:rounded-bl-none",
                current && "text-rail-foreground before:block md:bg-rail-active",
              )}
            >
              <Icon aria-hidden className="size-[21px]" />
              {label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
