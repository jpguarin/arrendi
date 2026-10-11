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

// Same origin: Next.js forwards /api to FastAPI (see next.config.ts).
export const api = createClient<paths>({ baseUrl: "" });
api.use(auth);
