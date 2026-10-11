"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/FormField";
import { MoneyField } from "@/components/MoneyField";
import { SelectField } from "@/components/SelectField";
import { DUE_DAY_OPTIONS } from "@/lib/labels";
import { email, requiredText } from "@/lib/validation";

const schema = z
  .object({
    unit: z.string().min(1, "Elige una unidad."),
    tenant_name: requiredText("Escribe el nombre del arrendatario."),
    tenant_email: email,
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
      rent: null,
      due_day: "",
      start_date: "",
      end_date: "",
      deposit: null,
      ...defaultValues,
    },
  });

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
