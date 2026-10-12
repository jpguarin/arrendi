"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/FormField";
import { MoneyField } from "@/components/MoneyField";
import { SelectField } from "@/components/SelectField";
import { FieldLegend, FieldSet } from "@/components/ui/field";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { DOCUMENT_TYPE_OPTIONS, type DocumentType, DUE_DAY_OPTIONS } from "@/lib/labels";
import { email, optionalText, requiredText } from "@/lib/validation";

const schema = z
  .object({
    unit: z.string().min(1, "Elige una unidad."),
    tenant_name: requiredText("Escribe el nombre del arrendatario."),
    tenant_email: email,
    tenant_document_type: z.enum(["cc", "nit"]),
    tenant_document_number: optionalText,
    rent: z
      .number()
      .nullable()
      .refine((value) => value !== null && value > 0, "Escribe el canon mensual."),
    due_day: z.string().min(1, "Elige el día de pago."),
    start_date: z.string().min(1, "Elige la fecha de inicio."),
    end_date: z.string(),
    deposit: z.number().nullable(),
  })
  // ISO dates compare as text.
  .refine((values) => !values.end_date || values.end_date > values.start_date, {
    path: ["end_date"],
    message: "Debe ser posterior a la fecha de inicio.",
  });
export type LeaseValues = z.infer<typeof schema>;

/** The tenant of the form, in the shape the API takes them. */
export function leaseTenant(values: LeaseValues) {
  return {
    name: values.tenant_name,
    email: values.tenant_email,
    document_type: values.tenant_document_type,
    document_number: values.tenant_document_number || null,
  };
}

/** The terms of the form, in the shape the API takes them. */
export function leaseTerms(values: LeaseValues) {
  return {
    rent: values.rent as number,
    due_day: Number(values.due_day),
    start_date: values.start_date,
    end_date: values.end_date || null,
    deposit: values.deposit,
  };
}

type LeaseFormProps = {
  /** The submit button lives in the screen's footer and points here with `form`. */
  id: string;
  /** Units to choose from. Without them the unit is already decided by the screen. */
  units?: readonly { value: string; label: string }[];
  defaultValues?: Partial<LeaseValues>;
  showDeposit?: boolean;
  /** The tenant's document, which the bill shows. The onboarding leaves it for later. */
  showTenantDocument?: boolean;
  onSubmit: (values: LeaseValues) => void | Promise<void>;
  /** Shown after the fields, inside the form: the document picker. */
  children?: React.ReactNode;
};

/** Tenant, rent, due day and dates of a lease. Used by the onboarding and by Contrato. */
export function LeaseForm({
  id,
  units,
  defaultValues,
  showDeposit = false,
  showTenantDocument = false,
  onSubmit,
  children,
}: LeaseFormProps) {
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<LeaseValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      // A screen that already knows the unit has nothing to choose.
      unit: units ? (units[0]?.value ?? "") : "fixed",
      tenant_name: "",
      tenant_email: "",
      tenant_document_type: "cc",
      tenant_document_number: "",
      rent: null,
      due_day: "",
      start_date: "",
      end_date: "",
      deposit: null,
      ...defaultValues,
    },
  });

  const isNit = useWatch({ control, name: "tenant_document_type" }) === "nit";

  return (
    <form id={id} onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-5">
      {units && (
        <Controller
          control={control}
          name="unit"
          render={({ field }) => (
            <SelectField
              id="unit"
              label="Unidad"
              options={units}
              value={field.value || undefined}
              onChange={field.onChange}
              placeholder="Elige una unidad"
              error={errors.unit?.message}
            />
          )}
        />
      )}
      <FormField
        id="tenant_name"
        label="Nombre del arrendatario"
        autoComplete="off"
        error={errors.tenant_name?.message}
        {...register("tenant_name")}
      />
      <FormField
        id="tenant_email"
        label="Correo del arrendatario"
        type="email"
        inputMode="email"
        autoComplete="off"
        autoCapitalize="none"
        description="Aquí le llegarán las cuentas, recordatorios y recibos."
        error={errors.tenant_email?.message}
        {...register("tenant_email")}
      />
      {showTenantDocument && (
        <>
          <FieldSet>
            <FieldLegend variant="label">Documento del arrendatario</FieldLegend>
            <Controller
              control={control}
              name="tenant_document_type"
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
            id="tenant_document_number"
            label={isNit ? "Número de NIT (opcional)" : "Número de cédula (opcional)"}
            description="Aparece en cada cuenta de cobro, junto al nombre."
            // A NIT carries a dash before its check digit.
            inputMode={isNit ? "text" : "numeric"}
            autoComplete="off"
            error={errors.tenant_document_number?.message}
            {...register("tenant_document_number")}
          />
        </>
      )}
      <div className="grid grid-cols-2 items-start gap-3">
        <Controller
          control={control}
          name="rent"
          render={({ field }) => (
            <MoneyField
              id="rent"
              label="Canon mensual"
              placeholder="$0"
              value={field.value}
              onChange={field.onChange}
              onBlur={field.onBlur}
              error={errors.rent?.message}
            />
          )}
        />
        <Controller
          control={control}
          name="due_day"
          render={({ field }) => (
            <SelectField
              id="due_day"
              label="Día de pago"
              options={DUE_DAY_OPTIONS}
              value={field.value || undefined}
              onChange={field.onChange}
              placeholder="Elige"
              error={errors.due_day?.message}
            />
          )}
        />
      </div>
      <div className="grid grid-cols-2 items-start gap-3">
        <FormField
          id="start_date"
          label="Inicio"
          type="date"
          error={errors.start_date?.message}
          {...register("start_date")}
        />
        <FormField
          id="end_date"
          label="Fin (opcional)"
          type="date"
          error={errors.end_date?.message}
          {...register("end_date")}
        />
      </div>
      {showDeposit && (
        <Controller
          control={control}
          name="deposit"
          render={({ field }) => (
            <MoneyField
              id="deposit"
              label="Depósito (opcional)"
              placeholder="$0"
              value={field.value}
              onChange={field.onChange}
              onBlur={field.onBlur}
              error={errors.deposit?.message}
            />
          )}
        />
      )}
      {children}
    </form>
  );
}
