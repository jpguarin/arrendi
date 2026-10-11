import type { Metadata } from "next";

import { AuthScreen } from "@/components/auth/AuthScreen";
import { LoginForm } from "@/components/auth/LoginForm";

export const metadata: Metadata = { title: "Ingresar · Arrendi" };

const LINK_ERRORS: Record<string, string> = {
  invalid_link: "El enlace no es válido o ya venció. Pide uno nuevo.",
};

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const { error } = await searchParams;
  const initialError = typeof error === "string" ? LINK_ERRORS[error] : undefined;

  return (
    <AuthScreen title="Ingresa a tu cuenta">
      <LoginForm initialError={initialError} />
    </AuthScreen>
  );
}
