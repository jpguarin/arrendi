import type { ApiError } from "./client";

export const CONNECTION_ERROR = "No pudimos conectarnos. Revisa tu conexión e inténtalo de nuevo.";

/** The message the API wrote for the owner, or a general one if it sent none. */
export function apiErrorMessage(error: ApiError | undefined): string {
  return error?.detail ?? "No pudimos completar la acción. Inténtalo de nuevo.";
}

/**
 * The message for whatever a query or a mutation failed with: the API's own message,
 * or the connection one when the request never got an answer.
 */
export function errorMessage(error: unknown): string {
  if (error && typeof error === "object" && "detail" in error && typeof error.detail === "string") {
    return error.detail;
  }
  return CONNECTION_ERROR;
}

/** Whether the API answered with this error code. */
export function hasCode(error: unknown, code: string): boolean {
  return Boolean(error && typeof error === "object" && "code" in error && error.code === code);
}
