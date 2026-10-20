"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { Controller, useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/FormField";
import { FieldLegend, FieldSet } from "@/components/ui/field";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { errorMessage } from "@/lib/api/errors";
import { useUpdateSettings } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { DOCUMENT_TYPE_OPTIONS, type DocumentType } from "@/lib/labels";
import { requiredText } from "@/lib/validation";

import { QuestionFrame } from "./QuestionFrame";
import { nextStep, profileHref } from "./steps";

type Settings = components["schemas"]["SettingsResponse"];

const schema = z.object({
  name: requiredText("Escribe tu nombre como debe salir en la cuenta."),
  document_type: z.enum(["cc", "nit"]),
  document_number: requiredText("Escribe el número de tu documento."),
});
type DocumentValues = z.infer<typeof schema>;

/** Who charges: the name, which comes from the sign-up, and the document. */
export function DocumentQuestion({ settings }: { settings: Settings }) {
  const router = useRouter();
  const update = useUpdateSettings();
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<DocumentValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: settings.name,
      document_type: settings.document_type,
      document_number: settings.document_number ?? "",
    },
  });
  const isNit = useWatch({ control, name: "document_type" }) === "nit";

  return (
    <QuestionFrame
      question="document"
      title="¿Cómo te identificas?"
      description="Va en la cuenta de cobro, junto a tu nombre."
      saving={update.isPending}
      error={update.error ? errorMessage(update.error) : undefined}
      onSubmit={handleSubmit((values) =>
        update.mutate(
          { body: values },
          { onSuccess: () => router.push(profileHref(nextStep("document"))) },
        ),
      )}
    >
      <FormField
        id="name"
        label="Tu nombre o razón social"
        autoComplete="name"
        description="Lo trajimos de tu cuenta. Cámbialo si quieres."
        error={errors.name?.message}
        {...register("name")}
      />
      <FieldSet>
        <FieldLegend variant="label">Tipo de documento</FieldLegend>
        <Controller
          control={control}
          name="document_type"
          render={({ field }) => (
            <ToggleGroup
              type="single"
              className="grid-cols-2"
              value={field.value}
              // Tapping the selected option again would clear it; keep it selected.
              onValueChange={(value) => value && field.onChange(value as DocumentType)}
            >
              {DOCUMENT_TYPE_OPTIONS.map((option) => (
                <ToggleGroupItem key={option.value} value={option.value}>
                  {option.label}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          )}
        />
      </FieldSet>
      <FormField
        id="document_number"
        label={isNit ? "Número de NIT" : "Número de cédula"}
        // A NIT carries a dash before its check digit.
        inputMode={isNit ? "text" : "numeric"}
        autoComplete="off"
        error={errors.document_number?.message}
        {...register("document_number")}
      />
    </QuestionFrame>
  );
}
