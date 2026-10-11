"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FormMessage } from "@/components/FormMessage";
import { ThemeSelector } from "@/components/ThemeSelector";
import { Button } from "@/components/ui/button";
import { api, type Me } from "@/lib/api/client";
import { createClient } from "@/lib/supabase/client";

const LOAD_ERROR = "No pudimos cargar tus datos. Revisa tu conexión e inténtalo de nuevo.";

// Provisional home: stage 5 replaces it with the summary of the month.
export function HomeScreen() {
  const router = useRouter();
  const [me, setMe] = useState<Me>();
  const [error, setError] = useState<string>();
  const [signingOut, setSigningOut] = useState(false);

  useEffect(() => {
    api
      .GET("/api/me")
      .then(({ data, error }) => {
        if (data) setMe(data);
        else setError(error?.detail ?? LOAD_ERROR);
      })
      .catch(() => setError(LOAD_ERROR));
  }, []);

  async function signOut() {
    setSigningOut(true);
    await createClient().auth.signOut();
    router.replace("/login");
    router.refresh();
  }

  return (
    <main className="flex flex-1 flex-col gap-8 px-5 py-10">
      <div className="flex flex-col gap-1">
        <p className="text-title-back font-bold text-primary">Arrendi</p>
        <h1 className="text-title font-bold" aria-live="polite">
          {me ? `Hola, ${me.name}` : "Hola"}
        </h1>
        {me && <p className="text-support text-muted-foreground">{me.email}</p>}
      </div>

      {error && <FormMessage tone="error">{error}</FormMessage>}

      <section className="flex flex-col gap-2">
        <h2 className="text-section font-semibold">Apariencia</h2>
        <ThemeSelector />
      </section>

      <Button variant="outline" size="md" onClick={signOut} disabled={signingOut}>
        {signingOut ? "Cerrando sesión…" : "Cerrar sesión"}
      </Button>
    </main>
  );
}
