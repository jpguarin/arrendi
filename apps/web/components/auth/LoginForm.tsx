"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthLink } from "@/components/auth/AuthLink";
import { FormField } from "@/components/FormField";
import { FormMessage } from "@/components/FormMessage";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";
import { authErrorMessage } from "@/lib/supabase/errors";
import { email } from "@/lib/validation";

const schema = z.object({
  email,
  password: z.string().min(1, "Escribe tu contraseña."),
});
type Values = z.infer<typeof schema>;

export function LoginForm({ initialError }: { initialError?: string }) {
  const router = useRouter();
  const [formError, setFormError] = useState(initialError);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  async function onSubmit(values: Values) {
    setFormError(undefined);
    const { error } = await createClient().auth.signInWithPassword(values);
    if (error) {
      setFormError(authErrorMessage(error));
      return;
    }
    router.replace("/");
    router.refresh();
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-5">
      {formError && <FormMessage tone="error">{formError}</FormMessage>}
      <FormField
        id="email"
        label="Correo"
        type="email"
        autoComplete="email"
        inputMode="email"
        error={errors.email?.message}
        {...register("email")}
      />
      <FormField
        id="password"
        label="Contraseña"
        type="password"
        autoComplete="current-password"
        error={errors.password?.message}
        {...register("password")}
      />
      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Ingresando…" : "Ingresar"}
      </Button>
      <div className="flex flex-col items-center">
        <AuthLink href="/reset-password">¿Olvidaste tu contraseña?</AuthLink>
        <AuthLink href="/signup">Crear una cuenta</AuthLink>
      </div>
    </form>
  );
}
