import type { AuthError } from "@supabase/supabase-js";

const MESSAGES: Record<string, string> = {
  invalid_credentials: "El correo o la contraseña no son correctos.",
  email_not_confirmed:
    "Todavía no has confirmado tu correo. Abre el enlace que te enviamos y vuelve a ingresar.",
  weak_password: "Esa contraseña es muy fácil de adivinar. Prueba con una más larga.",
  same_password: "La contraseña nueva debe ser distinta a la anterior.",
  over_email_send_rate_limit:
    "Ya te enviamos un correo hace poco. Espera un minuto antes de pedir otro.",
  over_request_rate_limit: "Hiciste muchos intentos seguidos. Espera un minuto y vuelve a probar.",
  session_not_found: "Tu sesión ya no es válida. Vuelve a ingresar.",
};

const FALLBACK = "No pudimos completar la acción. Inténtalo de nuevo.";

/** Turns a Supabase Auth error into a message for the owner. */
export function authErrorMessage(error: AuthError): string {
  return (error.code && MESSAGES[error.code]) || FALLBACK;
}
