import type { ApiError } from "./client";

export const CONNECTION_ERROR = "No pudimos conectarnos. Revisa tu conexión e inténtalo de nuevo.";

/** The message the API wrote for the owner, or a general one if it sent none. */
export function apiErrorMessage(error: ApiError | undefined): string {
  return error?.detail ?? "No pudimos completar la acción. Inténtalo de nuevo.";
}
