import { api } from "./client";
import { apiErrorMessage, CONNECTION_ERROR } from "./errors";

// The same limits the API enforces; checking here saves the owner a failed upload.
export const DOCUMENT_TYPES = ["application/pdf", "image/jpeg", "image/png"];
const MAX_SIZE = 10 * 1024 * 1024;

/** Why this file cannot be a lease document, or undefined if it can. */
export function documentProblem(file: File): string | undefined {
  if (!DOCUMENT_TYPES.includes(file.type)) return "Solo se aceptan archivos PDF, JPG o PNG.";
  if (file.size > MAX_SIZE) return "El archivo supera los 10 MB.";
  if (file.size === 0) return "El archivo está vacío.";
  return undefined;
}

/**
 * Attaches the signed lease to a lease. Returns an error message, or undefined if it worked.
 *
 * The file does not go through the API, which cannot take large requests: the API hands
 * out a signed link, the browser sends the file straight to storage, and the API then
 * checks what arrived.
 */
export async function uploadLeaseDocument(leaseId: string, file: File): Promise<string | undefined> {
  const problem = documentProblem(file);
  if (problem) return problem;

  try {
    const path = { lease_id: leaseId };
    const link = await api.POST("/api/leases/{lease_id}/document/upload-url", {
      params: { path },
      body: { filename: file.name, content_type: file.type, size: file.size },
    });
    if (!link.data) return apiErrorMessage(link.error);

    const sent = await fetch(link.data.upload_url, {
      method: "PUT",
      headers: { "Content-Type": file.type },
      body: file,
    });
    if (!sent.ok) return "No pudimos subir el archivo. Inténtalo de nuevo.";

    const confirmed = await api.POST("/api/leases/{lease_id}/document", {
      params: { path },
      body: { path: link.data.path },
    });
    return confirmed.data ? undefined : apiErrorMessage(confirmed.error);
  } catch {
    return CONNECTION_ERROR;
  }
}
