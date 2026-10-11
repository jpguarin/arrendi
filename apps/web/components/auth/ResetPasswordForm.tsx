"use client";

import { zodResolver } from "@hookform/resolvers/zod";
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

const schema = z.object({ email });
type Values = z.infer<typeof schema>;

export function ResetPasswordForm() {
  const [formError, setFormError] = useState<string>();
  const [sentTo, setSentTo] = useState<string>();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  async function onSubmit(values: Values) {
    setFormError(undefined);
    const { error } = await createClient().auth.resetPasswordForEmail(values.email, {
      redirectTo: `${window.location.origin}/auth/confirm?next=/update-password`,
    });
    if (error) {
      setFormError(authErrorMessage(error));
      return;
    }
    setSentTo(values.email);
  }

  if (sentTo) {
    return (
      <div className="flex flex-col gap-5">
        <FormMessage tone="success">
          Si {sentTo} tiene una cuenta, le enviamos un enlace para cambiar la contraseña.
        </FormMessage>
        <div className="flex flex-col items-center">
          <AuthLink href="/login">Volver a ingresar</AuthLink>
        </div>
      </div>
    );
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
      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Enviando…" : "Enviar enlace"}
      </Button>
      <div className="flex flex-col items-center">
        <AuthLink href="/login">Volver a ingresar</AuthLink>
      </div>
    </form>
  );
}
