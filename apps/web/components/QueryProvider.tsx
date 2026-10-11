"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { createClient } from "@/lib/supabase/client";

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Show what is in memory and always ask again: a screen opens at once and
        // never stays with old data.
        staleTime: 0,
        gcTime: 5 * 60 * 1000,
        // One more try when the network failed. An answer from the API (it has a
        // `code`) will not change by asking again.
        retry: (failures, error) =>
          failures < 1 && !(error && typeof error === "object" && "code" in error),
      },
    },
  });
}

/**
 * Keeps what the API answered in memory while the owner moves between screens.
 *
 * Only in memory: nothing is saved on the device, and it is emptied when the session
 * changes, so one account never sees what another one loaded.
 */
export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [client] = useState(createQueryClient);
  // Undefined until Supabase reports the session for the first time.
  const userId = useRef<string | null | undefined>(undefined);

  useEffect(() => {
    const { data } = createClient().auth.onAuthStateChange((_event, session) => {
      const current = session?.user.id ?? null;
      if (userId.current !== undefined && userId.current !== current) client.clear();
      userId.current = current;
    });
    return () => data.subscription.unsubscribe();
  }, [client]);

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
