"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/FormField";
import { itemErrors, ItemsField, itemsTotal, MAX_ITEMS } from "@/components/ItemsField";
import { MoneyField } from "@/components/MoneyField";
import { SelectField } from "@/components/SelectField";
import { TextareaField } from "@/components/TextareaField";
import { FieldLegend, FieldSet } from "@/components/ui/field";
import { Switch } from "@/components/ui/switch";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
  type DocumentType,
  DUE_DAY_OPTIONS,
  TENANT_DOCUMENT_TYPE,
  TENANT_DOCUMENT_TYPE_OPTIONS,
} from "@/lib/labels";
import { formatPesos, parsePercent, percentOf } from "@/lib/format";
import { email, item, optionalText, paymentDetails, requiredText } from "@/lib/validation";

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
    charge_deposit: z.boolean(),
    items: z.array(item).max(MAX_ITEMS),
    late_fee_enabled: z.boolean(),
    // As typed: "5", "2,5". Read with `parsePercent`.
    late_fee_percent: z.string(),
    late_fee_grace_days: z.string(),
    payment_details: paymentDetails,
  })
  // Only while the late fee is on: its fields are hidden otherwise, and an error on a
  // field that is not there would stop the form without saying why.
  .refine((values) => !values.late_fee_enabled || parsePercent(values.late_fee_percent), {
    path: ["late_fee_percent"],
    message: "Escribe un porcentaje mayor que 0, hasta 100 y con dos decimales como mucho.",
  })
  .refine((values) => !values.late_fee_enabled || graceDays(values.late_fee_grace_days) !== null, {
    path: ["late_fee_grace_days"],
    message: "Escribe un número de 0 a 30.",
  })
  // ISO dates compare as text.
  .refine((values) => !values.end_date || values.end_date > values.start_date, {
    path: ["end_date"],
    message: "Debe ser posterior a la fecha de inicio.",
  });
export type LeaseValues = z.infer<typeof schema>;

/** The days of grace as typed, from 0 to 30, or null if they are not that. */
function graceDays(text: string): number | null {
  return /^(\d|[12]\d|30)$/.test(text.trim()) ? Number(text) : null;
}

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
    charge_deposit: values.charge_deposit,
    items: values.items.map((charged) => ({ ...charged, amount: charged.amount ?? 0 })),
    late_fee_enabled: values.late_fee_enabled,
    // With the late fee off these are not checked, so whatever is not valid is left out:
    // the lease keeps what it had, to turn the fee back on as it was.
    late_fee_percent: parsePercent(values.late_fee_percent) ?? undefined,
    late_fee_grace_days: graceDays(values.late_fee_grace_days) ?? undefined,
    payment_details: values.payment_details || null,
  };
}

/** The terms of a lease that does not exist yet: nothing to keep, so nothing is left out. */
export function newLeaseTerms(values: LeaseValues) {
  const terms = leaseTerms(values);
  return { ...terms, late_fee_grace_days: terms.late_fee_grace_days ?? 0 };
}

type LeaseFormProps = {
  /** The submit button lives in the screen's footer and points here with `form`. */
  id: string;
  /** Units to choose from. Without them the unit is already decided by the screen. */
  units?: readonly { value: string; label: string }[];
  defaultValues?: Partial<LeaseValues>;
  showDeposit?: boolean;
  /** Whether the first monthly bill charges the deposit. Pointless once that bill exists. */
  showChargeDeposit?: boolean;
  /** What the lease charges every month besides the rent, like the building fee. */
  showItems?: boolean;
  /** What paying the rent late costs, when the lease says so. */
  showLateFee?: boolean;
  /** The tenant's document, which the bill shows. The onboarding leaves it for later. */
  showTenantDocument?: boolean;
  /** How to pay this lease's bills, when it is not as Ajustes says. */
  showPaymentDetails?: boolean;
  onSubmit: (values: LeaseValues) => void | Promise<void>;
  /** Called with what is typed, as it is typed: the onboarding keeps it as a draft. */
  onValuesChange?: (values: Partial<LeaseValues>) => void;
  /** Shown after the fields, inside the form: the document picker. */
  children?: React.ReactNode;
};

/** Tenant, rent, due day and dates of a lease. Used by the onboarding and by Contrato. */
export function LeaseForm({
  id,
  units,
  defaultValues,
  showDeposit = false,
  showChargeDeposit = false,
  showItems = false,
  showLateFee = false,
  showTenantDocument = false,
  showPaymentDetails = false,
  onSubmit,
  onValuesChange,
  children,
}: LeaseFormProps) {
  const {
    register,
    control,
    handleSubmit,
    subscribe,
    formState: { errors },
  } = useForm<LeaseValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      // A screen that already knows the unit has nothing to choose.
      unit: units ? (units[0]?.value ?? "") : "fixed",
      tenant_name: "",
      tenant_email: "",
      tenant_document_type: TENANT_DOCUMENT_TYPE,
      tenant_document_number: "",
      rent: null,
      due_day: "",
      start_date: "",
      end_date: "",
      deposit: null,
      charge_deposit: true,
      items: [],
      late_fee_enabled: false,
      late_fee_percent: "",
      late_fee_grace_days: "0",
      payment_details: "",
      ...defaultValues,
    },
  });

  useEffect(() => {
    if (!onValuesChange) return;
    return subscribe({ formState: { values: true }, callback: ({ values }) => onValuesChange(values) });
  }, [subscribe, onValuesChange]);

  const isNit = useWatch({ control, name: "tenant_document_type" }) === "nit";
  const hasDeposit = Boolean(useWatch({ control, name: "deposit" }));
  const rent = useWatch({ control, name: "rent" });
  const items = useWatch({ control, name: "items" });
  const lateFeeOn = useWatch({ control, name: "late_fee_enabled" });
  const lateFeePercent = parsePercent(useWatch({ control, name: "late_fee_percent" }));

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
                  {TENANT_DOCUMENT_TYPE_OPTIONS.map((option) => (
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
      {showDeposit && showChargeDeposit && hasDeposit && (
        <label className="flex min-h-11 items-center justify-between gap-3 rounded-xl border border-border bg-card p-4">
          <span className="flex flex-col gap-0.5">
            <span className="text-section">Cobrar el depósito en la primera cuenta</span>
            <span className="text-support text-muted-foreground">
              Sale como un ítem aparte, sumado al canon. Apágalo si ya te lo pagaron.
            </span>
          </span>
          <Controller
            control={control}
            name="charge_deposit"
            render={({ field }) => (
              <Switch checked={field.value} onCheckedChange={field.onChange} />
            )}
          />
        </label>
      )}
      {showItems && (
        <FieldSet>
          <FieldLegend variant="label">Otros conceptos del mes (opcional)</FieldLegend>
          <p className="text-support text-muted-foreground">
            Lo que cobras cada mes además del canon, como la administración. Salen en cada
            cuenta del mes, cada uno con su valor.
          </p>
          <Controller
            control={control}
            name="items"
            render={({ field }) => (
              <ItemsField
                id="lease-item"
                placeholder="Administración"
                value={field.value}
                onChange={field.onChange}
                errors={itemErrors(errors.items)}
              />
            )}
          />
          {items.length > 0 && (
            <div className="flex items-baseline justify-between gap-3 rounded-xl border border-border bg-card p-4">
              <p className="text-section font-semibold">Total de cada mes</p>
              <p className="text-title font-bold">
                {formatPesos((rent ?? 0) + itemsTotal(items))}
              </p>
            </div>
          )}
        </FieldSet>
      )}
      {showLateFee && (
        <>
          <label className="flex min-h-11 items-center justify-between gap-3 rounded-xl border border-border bg-card p-4">
            <span className="flex flex-col gap-0.5">
              <span className="text-section">Cobrar recargo por mora</span>
              <span className="text-support text-muted-foreground">
                Si el canon no se paga a tiempo, la cuenta del mes siguiente trae un recargo,
                una sola vez. Actívalo solo si tu contrato lo dice.
              </span>
            </span>
            <Controller
              control={control}
              name="late_fee_enabled"
              render={({ field }) => (
                <Switch checked={field.value} onCheckedChange={field.onChange} />
              )}
            />
          </label>
          {lateFeeOn && (
            <div className="grid grid-cols-2 items-start gap-3">
              <FormField
                id="late_fee_percent"
                label="Porcentaje del canon"
                placeholder="5"
                inputMode="decimal"
                autoComplete="off"
                description={
                  rent && lateFeePercent
                    ? `Con este canon, el recargo es de ${formatPesos(percentOf(rent, lateFeePercent))}.`
                    : "Por ejemplo 5 o 2,5."
                }
                error={errors.late_fee_percent?.message}
                {...register("late_fee_percent")}
              />
              <FormField
                id="late_fee_grace_days"
                label="Días de gracia"
                inputMode="numeric"
                autoComplete="off"
                description="Después del vencimiento, antes de que aplique."
                error={errors.late_fee_grace_days?.message}
                {...register("late_fee_grace_days")}
              />
            </div>
          )}
        </>
      )}
      {showPaymentDetails && (
        <TextareaField
          id="payment_details"
          label="Cómo te pagan (opcional)"
          placeholder="Banco, tipo y número de cuenta, Nequi…"
          description="Solo para las cuentas de este contrato. Si lo dejas vacío, se usan los de Ajustes."
          rows={3}
          error={errors.payment_details?.message}
          {...register("payment_details")}
        />
      )}
      {children}
    </form>
  );
}
