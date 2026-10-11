import { z } from "zod";

// Shape checks for the browser only. The rules that matter are enforced by the API
// and by Supabase Auth.
export const email = z.email("Escribe un correo válido.");
export const newPassword = z.string().min(8, "Usa al menos 8 caracteres.");

/** A text the owner must fill in. The API trims it and has the last word on its length. */
export const requiredText = (message: string) =>
  z.string().trim().min(1, message).max(120, "Usa 120 caracteres o menos.");

/** A text the owner may leave empty. */
export const optionalText = z.string().trim().max(200, "Usa 200 caracteres o menos.");
