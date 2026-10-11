import createClient, { type Middleware } from "openapi-fetch";

import { createClient as createSupabaseClient } from "@/lib/supabase/client";

import type { components, paths } from "./schema";

/** The body of every error response: a message for the owner and a stable code. */
export type ApiError = components["schemas"]["ErrorResponse"];
export type Me = components["schemas"]["MeResponse"];

const auth: Middleware = {
  async onRequest({ request }) {
    // In the browser, `getSession` refreshes the token when it is about to expire.
    const { data } = await createSupabaseClient().auth.getSession();
    if (data.session) {
      request.headers.set("Authorization", `Bearer ${data.session.access_token}`);
    }
    return request;
  },
  async onResponse({ response }) {
    if (response.status === 401) {
      // The API no longer accepts the session: clear it and start over.
      await createSupabaseClient().auth.signOut({ scope: "local" });
      // A full page load on purpose, to drop everything the old session left in memory.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign("/login");
    }
    return response;
  },
};

// Reads that are on their way, by address and session.
const inFlight = new Map<string, Promise<Response>>();

/**
 * Sends a read only once while it is on its way: whoever asks for the same thing in
 * the meantime gets the same answer.
 *
 * Two parts of a screen often need the same data at the same moment, and in development
 * React mounts every screen twice on purpose, which sent every first load twice.
 * Nothing is kept once the answer arrives, so the next visit asks again.
 */
async function fetchOnce(request: Request): Promise<Response> {
  if (request.method !== "GET") return fetch(request);

  const key = `${request.url}\n${request.headers.get("Authorization") ?? ""}`;
  let pending = inFlight.get(key);
  if (!pending) {
    pending = fetch(request).finally(() => inFlight.delete(key));
    inFlight.set(key, pending);
  }
  // Each caller reads its own copy; a response can only be read once.
  return (await pending).clone();
}

// Same origin: Next.js forwards /api to FastAPI (see next.config.ts).
export const api = createClient<paths>({ baseUrl: "", fetch: fetchOnce });
api.use(auth);
