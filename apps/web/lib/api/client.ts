import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

/** The body of every error response: a message for the owner and a stable code. */
export type ApiError = components["schemas"]["ErrorResponse"];

// Same origin: Next.js forwards /api to FastAPI (see next.config.ts).
export const api = createClient<paths>({ baseUrl: "" });
