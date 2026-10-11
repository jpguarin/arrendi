import type { Metadata } from "next";

import { AuthScreen } from "@/components/auth/AuthScreen";
import { UpdatePasswordForm } from "@/components/auth/UpdatePasswordForm";

export const metadata: Metadata = { title: "Contraseña nueva · Arrendi" };

export default function UpdatePasswordPage() {
  return (
    <AuthScreen title="Crea una contraseña nueva">
      <UpdatePasswordForm />
    </AuthScreen>
  );
}
