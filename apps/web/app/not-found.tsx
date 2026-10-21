import type { Metadata } from "next";
import { LayoutDashboard } from "lucide-react";
import Link from "next/link";

import { BackButton } from "@/components/BackButton";
import { Brand } from "@/components/Brand";
import { EmptyHouse } from "@/components/EmptyHouse";
import { NotFoundAddress } from "@/components/NotFoundAddress";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = { title: "Página no encontrada · Arrendi" };

// An address that leads nowhere: proposal 2, "Aquí no vive nadie", of
// docs/new-brand-design/mockups/pagina-404. The proxy sends whoever is signed out to
// sign in first, so whoever sees it has a session.
export default function NotFound() {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="px-4 py-3.5 md:px-8 md:py-5">
        <Brand />
      </header>
      {/* grid-cols-1 on a phone: an implicit column would grow to fit a long address. */}
      <main className="mx-auto grid w-full max-w-5xl flex-1 grid-cols-1 content-center justify-items-center gap-7 px-5 pt-4 pb-12 text-center md:grid-cols-2 md:justify-items-start md:gap-12 md:px-8 md:pb-16 md:text-left">
        <div className="flex max-w-full flex-col items-center gap-4.5 md:justify-self-end">
          <EmptyHouse />
          <NotFoundAddress />
        </div>
        <div className="flex w-full flex-col items-center gap-2.5 md:items-start md:pt-5">
          <p className="text-support font-semibold text-muted-foreground">Error 404</p>
          <h1 className="text-figure font-black">Aquí no vive nadie</h1>
          <p className="max-w-md text-section text-muted-foreground">
            Esta dirección no lleva a ninguna página de Arrendi. Revisa el enlace o vuelve a tu
            resumen.
          </p>
          <div className="mt-3.5 flex w-full flex-col gap-2.5 sm:flex-row sm:justify-center md:justify-start">
            <Button asChild>
              <Link href="/">
                <LayoutDashboard aria-hidden />
                Ir al resumen
              </Link>
            </Button>
            <BackButton />
          </div>
        </div>
      </main>
    </div>
  );
}
