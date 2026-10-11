import type { Metadata } from "next";

import { AuthScreen } from "@/components/auth/AuthScreen";
import { EmailDivider } from "@/components/auth/EmailDivider";
import { GoogleButton } from "@/components/auth/GoogleButton";
import { LoginForm } from "@/components/auth/LoginForm";

export const metadata: Metadata = { title: "Ingresar · Arrendi" };

const LINK_ERRORS: Record<string, string> = {
  invalid_link: "El enlace no es válido o ya venció. Pide uno nuevo.",
  google_failed: "No pudimos ingresar con Google. Inténtalo de nuevo.",
};

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const { error } = await searchParams;
  const initialError = typeof error === "string" ? LINK_ERRORS[error] : undefined;

  return (
    <AuthScreen title="Ingresa a tu cuenta">
      <GoogleButton />
      <EmailDivider />
      <LoginForm initialError={initialError} />
    </AuthScreen>
  );
}
