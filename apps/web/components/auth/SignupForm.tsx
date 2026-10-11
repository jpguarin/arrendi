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
import { email, newPassword } from "@/lib/validation";

const schema = z.object({
  name: z.string().trim().min(1, "Escribe tu nombre."),
  email,
  password: newPassword,
});
type Values = z.infer<typeof schema>;

export function SignupForm() {
  const router = useRouter();
  const [formError, setFormError] = useState<string>();
  const [sentTo, setSentTo] = useState<string>();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  async function onSubmit(values: Values) {
    setFormError(undefined);
    const { data, error } = await createClient().auth.signUp({
      email: values.email,
      password: values.password,
      options: {
        // The API reads the name from the token, the same as with Google.
        data: { full_name: values.name },
        emailRedirectTo: `${window.location.origin}/auth/confirm?next=/`,
      },
    });
    if (error) {
      setFormError(authErrorMessage(error));
      return;
    }
    if (data.session) {
      // The project does not ask to confirm the email.
      router.replace("/");
      router.refresh();
      return;
    }
    setSentTo(values.email);
  }

  if (sentTo) {
    return (
      <div className="flex flex-col gap-5">
        <FormMessage tone="success">
          Te enviamos un correo a {sentTo}. Abre el enlace para confirmar tu cuenta y después
          ingresa.
        </FormMessage>
        <div className="flex flex-col items-center">
          <AuthLink href="/login">Ir a ingresar</AuthLink>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-5">
      {formError && <FormMessage tone="error">{formError}</FormMessage>}
      <FormField
        id="name"
        label="Nombre"
        autoComplete="name"
        description="Aparece en las cuentas de cobro que envías."
        error={errors.name?.message}
        {...register("name")}
      />
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
        autoComplete="new-password"
        description="Al menos 8 caracteres."
        error={errors.password?.message}
        {...register("password")}
      />
      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Creando tu cuenta…" : "Crear cuenta"}
      </Button>
      <div className="flex flex-col items-center">
        <AuthLink href="/login">Ya tengo una cuenta</AuthLink>
      </div>
    </form>
  );
}
