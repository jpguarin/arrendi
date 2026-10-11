"use client";

import { useState } from "react";

import { FormMessage } from "@/components/FormMessage";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";
import { authErrorMessage } from "@/lib/supabase/errors";

// Google's logo. Its colors are fixed by Google's brand rules, so they are the one
// exception to "no hand-written colors": they must not change with the theme.
function GoogleLogo() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path
        fill="#4285F4"
        d="M23.49 12.27c0-.79-.07-1.54-.19-2.27H12v4.51h6.47c-.29 1.48-1.14 2.73-2.4 3.58v3h3.86c2.26-2.09 3.56-5.17 3.56-8.82Z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.86-3c-1.08.72-2.45 1.16-4.07 1.16-3.13 0-5.78-2.11-6.73-4.96H1.29v3.09C3.26 21.3 7.31 24 12 24Z"
      />
      <path
        fill="#FBBC05"
        d="M5.27 14.29c-.25-.72-.38-1.49-.38-2.29s.14-1.57.38-2.29V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.98-3.09Z"
      />
      <path
        fill="#EA4335"
        d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.98 3.09c.95-2.85 3.6-4.96 6.73-4.96Z"
      />
    </svg>
  );
}

/** Main way in: leaves for Google's page and comes back through /auth/callback. */
export function GoogleButton() {
  const [opening, setOpening] = useState(false);
  const [error, setError] = useState<string>();

  async function signIn() {
    if (!navigator.onLine) {
      // Leaving for Google without a connection would land on the browser's error page.
      setError("No hay conexión. Revisa tu internet e inténtalo de nuevo.");
      return;
    }
    setOpening(true);
    setError(undefined);
    const { error } = await createClient().auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback?next=/` },
    });
    if (error) {
      setError(authErrorMessage(error));
      setOpening(false);
    }
    // Without an error the browser is already on its way to Google.
  }

  return (
    <div className="flex flex-col gap-3">
      {error && <FormMessage tone="error">{error}</FormMessage>}
      <Button type="button" variant="outline" className="w-full" onClick={signIn} disabled={opening}>
        <GoogleLogo />
        {opening ? "Abriendo Google…" : "Continuar con Google"}
      </Button>
    </div>
  );
}
