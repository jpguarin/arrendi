import type { Metadata } from "next";

import { Brand } from "@/components/Brand";
import { Column } from "@/components/Column";
import { RetryButton } from "@/components/RetryButton";

export const metadata: Metadata = { title: "Sin conexión · Arrendi" };

// The service worker shows this screen when a page cannot be loaded.
export default function OfflinePage() {
  return (
    <Column>
    <main className="flex flex-1 flex-col justify-center gap-6 px-5 py-10">
      <Brand />
      <div className="flex flex-col gap-1">
        <h1 className="text-title font-bold">No hay conexión</h1>
        <p className="text-support text-muted-foreground">
          Arrendi necesita internet para consultar y registrar. Revisa tu conexión e inténtalo de
          nuevo.
        </p>
      </div>
      <RetryButton />
    </main>
    </Column>
  );
}
