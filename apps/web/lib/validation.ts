import { z } from "zod";

// Shape checks for the browser only. The rules that matter are enforced by the API
// and by Supabase Auth.
export const email = z.email("Escribe un correo válido.");
export const newPassword = z.string().min(8, "Usa al menos 8 caracteres.");
