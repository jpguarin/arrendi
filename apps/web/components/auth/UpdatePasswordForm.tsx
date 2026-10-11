"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/FormField";
import { FormMessage } from "@/components/FormMessage";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";
import { authErrorMessage } from "@/lib/supabase/errors";
import { newPassword } from "@/lib/validation";

const schema = z.object({ password: newPassword });
type Values = z.infer<typeof schema>;

export function UpdatePasswordForm() {
  const router = useRouter();
  const [formError, setFormError] = useState<string>();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  async function onSubmit(values: Values) {
    setFormError(undefined);
    const { error } = await createClient().auth.updateUser({ password: values.password });
    if (error) {
      setFormError(authErrorMessage(error));
      return;
    }
    router.replace("/");
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-5">
      {formError && <FormMessage tone="error">{formError}</FormMessage>}
      <FormField
        id="password"
        label="Contraseña nueva"
        type="password"
        autoComplete="new-password"
        description="Al menos 8 caracteres."
        error={errors.password?.message}
        {...register("password")}
      />
      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Guardando…" : "Guardar contraseña"}
      </Button>
    </form>
  );
}
