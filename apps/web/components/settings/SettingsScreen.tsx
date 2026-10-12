"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/FormField";
import { FormMessage } from "@/components/FormMessage";
import { Header } from "@/components/Header";
import { LoadError, Loading } from "@/components/LoadState";
import { SelectField } from "@/components/SelectField";
import { SignOutButton } from "@/components/SignOutButton";
import { TextareaField } from "@/components/TextareaField";
import { ThemeSelector } from "@/components/ThemeSelector";
import { Button } from "@/components/ui/button";
import { FieldLegend, FieldSet } from "@/components/ui/field";
import { Switch } from "@/components/ui/switch";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { errorMessage } from "@/lib/api/errors";
import { useSettings, useUpdateSettings } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { DOCUMENT_TYPE_OPTIONS, type DocumentType, SEND_DAY_OPTIONS } from "@/lib/labels";
import { optionalText, requiredText } from "@/lib/validation";

type Settings = components["schemas"]["SettingsResponse"];

const schema = z.object({
  name: requiredText("Escribe tu nombre."),
  document_type: z.enum(["cc", "nit"]),
  document_number: optionalText,
  payment_details: z.string().trim().max(500, "Usa 500 caracteres o menos."),
  send_day: z.string().min(1),
  reminder_1: z.boolean(),
  reminder_2: z.boolean(),
  email_copy: z.boolean(),
});
type SettingsValues = z.infer<typeof schema>;

const toValues = (settings: Settings): SettingsValues => ({
  name: settings.name,
  document_type: settings.document_type,
  document_number: settings.document_number ?? "",
  payment_details: settings.payment_details ?? "",
  send_day: String(settings.send_day),
  reminder_1: settings.reminder_1,
  reminder_2: settings.reminder_2,
  email_copy: settings.email_copy,
});

const SENDING_SWITCHES = [
  { name: "reminder_1", label: "Recordatorio al día siguiente del vencimiento" },
  { name: "reminder_2", label: "Segundo recordatorio a los 7 días" },
  { name: "email_copy", label: "Recibir copia de cada correo" },
] as const;

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
      { body: { ...values, send_day: Number(values.send_day) } },
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

      <section aria-labelledby="sending" className="flex flex-col gap-5">
        <div className="flex flex-col gap-0.5">
          <h2 id="sending" className="text-section font-semibold">
            Envíos por correo
          </h2>
          <p className="text-support text-muted-foreground">
            Ese día se generan las cuentas del mes y se envían a los contratos con envío
            automático.
          </p>
        </div>
        <Controller
          control={control}
          name="send_day"
          render={({ field }) => (
            <SelectField
              id="send_day"
              label="Enviar las cuentas"
              options={SEND_DAY_OPTIONS}
              value={field.value}
              onChange={field.onChange}
            />
          )}
        />
        <div className="flex flex-col rounded-xl border border-border bg-card px-4">
          {SENDING_SWITCHES.map(({ name, label }) => (
            <label
              key={name}
              className="flex min-h-14 items-center justify-between gap-3 border-t border-border py-2 first:border-t-0"
            >
              <span className="text-section">{label}</span>
              <Controller
                control={control}
                name={name}
                render={({ field }) => (
                  <Switch checked={field.value} onCheckedChange={field.onChange} />
                )}
              />
            </label>
          ))}
        </div>
      </section>

      <Button type="submit" disabled={update.isPending}>
        {update.isPending ? "Guardando…" : "Guardar"}
      </Button>
    </form>
  );
}

/** Who the owner is, how they get paid, when the bills go out, and the theme. */
export function SettingsScreen() {
  const { data: settings, error, refetch } = useSettings();

  return (
    <>
      <Header title="Ajustes" />
      <main className="flex flex-1 flex-col gap-4 px-5 pt-2 pb-8">
        {settings ? (
          <>
            <SettingsForm settings={settings} />
            {/* Kept on the device, not in the account: it has no "save". */}
            <section aria-labelledby="appearance" className="flex flex-col gap-3 pt-4">
              <h2 id="appearance" className="text-section font-semibold">
                Apariencia
              </h2>
              <ThemeSelector />
            </section>
            <div className="grid pt-4">
              <SignOutButton />
            </div>
          </>
        ) : error ? (
          <LoadError message={errorMessage(error)} onRetry={refetch} />
        ) : (
          <Loading label="Cargando tus ajustes" />
        )}
      </main>
    </>
  );
}
