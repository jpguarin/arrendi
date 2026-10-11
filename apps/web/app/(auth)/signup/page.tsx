import type { Metadata } from "next";

import { AuthScreen } from "@/components/auth/AuthScreen";
import { EmailDivider } from "@/components/auth/EmailDivider";
import { GoogleButton } from "@/components/auth/GoogleButton";
import { SignupForm } from "@/components/auth/SignupForm";

export const metadata: Metadata = { title: "Crear cuenta · Arrendi" };

export default function SignupPage() {
  return (
    <AuthScreen
      title="Crea tu cuenta"
      description="Genera tus cuentas de cobro y sabe quién te debe."
    >
      <GoogleButton />
      <EmailDivider />
      <SignupForm />
    </AuthScreen>
  );
}
