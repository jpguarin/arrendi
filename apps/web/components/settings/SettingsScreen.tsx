"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/FormField";
import { FormMessage } from "@/components/FormMessage";
import { Header } from "@/components/Header";
import { LoadError, Loading } from "@/components/LoadState";
import { TextareaField } from "@/components/TextareaField";
import { Button } from "@/components/ui/button";
import { FieldLegend, FieldSet } from "@/components/ui/field";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { errorMessage } from "@/lib/api/errors";
import { useSettings, useUpdateSettings } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { DOCUMENT_TYPE_OPTIONS, type DocumentType } from "@/lib/labels";
import { optionalText, requiredText } from "@/lib/validation";

type Settings = components["schemas"]["SettingsResponse"];

const schema = z.object({
  name: requiredText("Escribe tu nombre."),
  document_type: z.enum(["cc", "nit"]),
  document_number: optionalText,
  payment_details: z.string().trim().max(500, "Usa 500 caracteres o menos."),
});
type SettingsValues = z.infer<typeof schema>;

const toValues = (settings: Settings): SettingsValues => ({
  name: settings.name,
  document_type: settings.document_type,
  document_number: settings.document_number ?? "",
  payment_details: settings.payment_details ?? "",
});

function SettingsForm({ settings }: { settings: Settings }) {
  const update = useUpdateSettings();
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<SettingsValues>({
    resolver: zodResolver(schema),
    defaultValues: toValues(settings),
  });

  const isNit = useWatch({ control, name: "document_type" }) === "nit";

  function save(values: SettingsValues) {
    update.mutate(
      { body: values },
      // What the API kept becomes the starting point, so "saved" lasts until the next change.
      { onSuccess: (saved) => reset(toValues(saved)) },
    );
  }

  return (
    <form onSubmit={handleSubmit(save)} noValidate className="flex flex-col gap-7">
      {update.error && <FormMessage tone="error">{errorMessage(update.error)}</FormMessage>}
      {update.isSuccess && !isDirty && <FormMessage tone="success">Datos guardados.</FormMessage>}

      <section aria-labelledby="owner-details" className="flex flex-col gap-5">
        <div className="flex flex-col gap-0.5">
          <h2 id="owner-details" className="text-section font-semibold">
            Tus datos
          </h2>
          <p className="text-support text-muted-foreground">
            Aparecen en el encabezado de cada cuenta de cobro.
          </p>
        </div>
        <FormField
          id="name"
          label="Nombre"
          autoComplete="name"
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
        <p className="text-support text-muted-foreground">
          Entras a Arrendi con {settings.email}.
        </p>
      </section>

      <section aria-labelledby="payment-details" className="flex flex-col gap-5">
        <h2 id="payment-details" className="text-section font-semibold">
          Datos de pago
        </h2>
        <TextareaField
          id="payment_details"
          label="Cómo te pagan"
          placeholder="Banco, tipo y número de cuenta, Nequi…"
          description="Aparece en cada cuenta de cobro, después de “Pagar a:”."
          rows={3}
          error={errors.payment_details?.message}
          {...register("payment_details")}
        />
      </section>

      <Button type="submit" disabled={update.isPending}>
        {update.isPending ? "Guardando…" : "Guardar"}
      </Button>
    </form>
  );
}

/** Who the owner is and how they get paid. The rest of the settings arrive in stage 4. */
export function SettingsScreen() {
  const { data: settings, error, refetch } = useSettings();

  return (
    <>
      <Header title="Ajustes" />
      <main className="flex flex-1 flex-col gap-4 px-5 pt-2 pb-8">
        {settings ? (
          <SettingsForm settings={settings} />
        ) : error ? (
          <LoadError message={errorMessage(error)} onRetry={refetch} />
        ) : (
          <Loading label="Cargando tus ajustes" />
        )}
      </main>
    </>
  );
}
