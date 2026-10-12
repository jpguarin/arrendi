import { api, type ApiError } from "./client";
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

type Answer<T> = { data?: T; error?: ApiError };

/**
 * Sends a file in three steps. Returns an error message, or undefined if it worked.
 *
 * The file does not go through the API, which cannot take large requests: the API hands
 * out a signed link, the browser sends the file straight to storage, and the API then
 * checks what arrived.
 */
async function sendFile(
  file: File,
  askForLink: () => Promise<Answer<{ upload_url: string; path: string }>>,
  confirm: (path: string) => Promise<Answer<unknown>>,
): Promise<string | undefined> {
  const problem = documentProblem(file);
  if (problem) return problem;

  try {
    const link = await askForLink();
    if (!link.data) return apiErrorMessage(link.error);

    const sent = await fetch(link.data.upload_url, {
      method: "PUT",
      headers: { "Content-Type": file.type },
      body: file,
    });
    if (!sent.ok) return "No pudimos subir el archivo. Inténtalo de nuevo.";

    const confirmed = await confirm(link.data.path);
    return confirmed.data ? undefined : apiErrorMessage(confirmed.error);
  } catch {
    return CONNECTION_ERROR;
  }
}

const describe = (file: File) => ({
  filename: file.name,
  content_type: file.type,
  size: file.size,
});

/** Attaches the signed lease to a lease. Returns an error message, or undefined. */
export function uploadLeaseDocument(leaseId: string, file: File): Promise<string | undefined> {
  const params = { path: { lease_id: leaseId } };
  return sendFile(
    file,
    () => api.POST("/api/leases/{lease_id}/document/upload-url", { params, body: describe(file) }),
    (path) => api.POST("/api/leases/{lease_id}/document", { params, body: { path } }),
  );
}

/** Attaches the proof of payment to a payment. Returns an error message, or undefined. */
export function uploadPaymentProof(paymentId: string, file: File): Promise<string | undefined> {
  const params = { path: { payment_id: paymentId } };
  return sendFile(
    file,
    () => api.POST("/api/payments/{payment_id}/proof/upload-url", { params, body: describe(file) }),
    (path) => api.POST("/api/payments/{payment_id}/proof", { params, body: { path } }),
  );
}

/**
 * Opens a private file in a new tab, with the temporary link the API hands out for it.
 * Returns an error message, or undefined if it worked. Call it straight from the tap.
 */
export async function openTemporaryLink(
  request: () => Promise<{ data?: { url: string }; error?: ApiError }>,
): Promise<string | undefined> {
  // Opened now, during the tap: a window opened after waiting for the API is blocked
  // as a pop-up, above all on iPhone.
  const tab = window.open("", "_blank");
  try {
    const { data, error } = await request();
    if (!data) {
      tab?.close();
      return apiErrorMessage(error);
    }
    if (tab) tab.location.href = data.url;
    else window.location.assign(data.url);
    return undefined;
  } catch {
    tab?.close();
    return CONNECTION_ERROR;
  }
}
