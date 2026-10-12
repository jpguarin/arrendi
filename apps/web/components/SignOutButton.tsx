"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";

export function SignOutButton() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [signingOut, setSigningOut] = useState(false);

  async function signOut() {
    setSigningOut(true);
    await createClient().auth.signOut();
    // The next account on this device must not see what this one loaded.
    queryClient.clear();
    router.replace("/login");
    router.refresh();
  }

  return (
    <Button variant="outline" size="md" onClick={signOut} disabled={signingOut}>
      {signingOut ? "Cerrando sesión…" : "Cerrar sesión"}
    </Button>
  );
}
