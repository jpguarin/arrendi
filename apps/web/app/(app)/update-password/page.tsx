import type { Metadata } from "next";

import { Column } from "@/components/Column";
import { AuthScreen } from "@/components/auth/AuthScreen";
import { UpdatePasswordForm } from "@/components/auth/UpdatePasswordForm";

export const metadata: Metadata = { title: "Contraseña nueva · Arrendi" };

export default function UpdatePasswordPage() {
  return (
    <Column>
      <AuthScreen title="Crea una contraseña nueva">
        <UpdatePasswordForm />
      </AuthScreen>
    </Column>
  );
}
