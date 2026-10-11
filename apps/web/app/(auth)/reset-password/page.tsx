import type { Metadata } from "next";

import { AuthScreen } from "@/components/auth/AuthScreen";
import { ResetPasswordForm } from "@/components/auth/ResetPasswordForm";

export const metadata: Metadata = { title: "Recuperar contraseña · Arrendi" };

export default function ResetPasswordPage() {
  return (
    <AuthScreen
      title="Recupera tu contraseña"
      description="Escribe tu correo y te enviamos un enlace para crear una nueva."
    >
      <ResetPasswordForm />
    </AuthScreen>
  );
}
