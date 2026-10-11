"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FormMessage } from "@/components/FormMessage";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/api/errors";
import { useMe } from "@/lib/api/queries";
import { createClient } from "@/lib/supabase/client";

// Provisional home: stage 5 replaces it with the summary of the month.
export function HomeScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data, error } = useMe();
  const [signingOut, setSigningOut] = useState(false);
  // Nothing to show yet: the owner starts by creating their first property.
  const onboarding = data?.onboarding_complete === false;
  const me = onboarding ? undefined : data;

  useEffect(() => {
    if (onboarding) router.replace("/onboarding/property");
  }, [onboarding, router]);

  async function signOut() {
    setSigningOut(true);
    await createClient().auth.signOut();
    // The next account on this device must not see what this one loaded.
    queryClient.clear();
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

      {error && !data && <FormMessage tone="error">{errorMessage(error)}</FormMessage>}

      <Button variant="outline" size="md" onClick={signOut} disabled={signingOut}>
        {signingOut ? "Cerrando sesión…" : "Cerrar sesión"}
      </Button>
    </main>
  );
}
