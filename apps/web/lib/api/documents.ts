import { api, type ApiError } from "./client";
import { apiErrorMessage, CONNECTION_ERROR } from "./errors";

// The same limits the API enforces; checking here saves the owner a failed upload.
const MB = 1024 * 1024;
type Limits = {
  types: readonly string[];
  maxSize: number;
  wrongType: string;
  tooLarge: string;
};

const DOCUMENT: Limits = {
  types: ["application/pdf", "image/jpeg", "image/png"],
  maxSize: 10 * MB,
  wrongType: "Solo se aceptan archivos PDF, JPG o PNG.",
  tooLarge: "El archivo supera los 10 MB.",
};
const SIGNATURE: Limits = {
  types: ["image/png", "image/jpeg"],
  maxSize: 2 * MB,
  wrongType: "Solo se aceptan imágenes JPG o PNG.",
  tooLarge: "La imagen supera los 2 MB.",
};
export const DOCUMENT_TYPES = DOCUMENT.types;
export const SIGNATURE_TYPES = SIGNATURE.types;

function fileProblem(file: File, limits: Limits): string | undefined {
  if (!limits.types.includes(file.type)) return limits.wrongType;
  if (file.size > limits.maxSize) return limits.tooLarge;
  if (file.size === 0) return "El archivo está vacío.";
  return undefined;
}

/** Why this file cannot be a lease document, or undefined if it can. */
export const documentProblem = (file: File) => fileProblem(file, DOCUMENT);

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
  limits: Limits = DOCUMENT,
): Promise<string | undefined> {
  const problem = fileProblem(file, limits);
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
    () =>
      api.POST("/api/leases/{lease_id}/document/upload-url", {
        params,
        body: describe(file),
      }),
    (path) => api.POST("/api/leases/{lease_id}/document", { params, body: { path } }),
  );
}

/** Attaches the inventory of the unit to a lease. Returns an error message, or undefined. */
export function uploadLeaseInventory(leaseId: string, file: File): Promise<string | undefined> {
  const params = { path: { lease_id: leaseId } };
  return sendFile(
    file,
    () =>
      api.POST("/api/leases/{lease_id}/inventory/upload-url", {
        params,
        body: describe(file),
      }),
    (path) => api.POST("/api/leases/{lease_id}/inventory", { params, body: { path } }),
  );
}

/** Attaches the proof of payment to a payment. Returns an error message, or undefined. */
export function uploadPaymentProof(paymentId: string, file: File): Promise<string | undefined> {
  const params = { path: { payment_id: paymentId } };
  return sendFile(
    file,
    () =>
      api.POST("/api/payments/{payment_id}/proof/upload-url", {
        params,
        body: describe(file),
      }),
    (path) => api.POST("/api/payments/{payment_id}/proof", { params, body: { path } }),
  );
}

/** Makes the image the owner's signature. Returns an error message, or undefined. */
export function uploadSignature(file: File): Promise<string | undefined> {
  return sendFile(
    file,
    () => api.POST("/api/settings/signature/upload-url", { body: describe(file) }),
    (path) => api.POST("/api/settings/signature", { body: { path } }),
    SIGNATURE,
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
