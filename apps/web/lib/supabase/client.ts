import { createBrowserClient } from "@supabase/ssr";

import { supabaseEnv } from "./env";

/** Supabase client for Client Components. Only used for signing in and out. */
export function createClient() {
  const { url, publishableKey } = supabaseEnv();
  return createBrowserClient(url, publishableKey);
}
