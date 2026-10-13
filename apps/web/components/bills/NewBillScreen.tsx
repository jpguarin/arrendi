"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Controller, useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/FormField";
import { FormMessage } from "@/components/FormMessage";
import { FormScreen, FormScreenFallback } from "@/components/FormScreen";
import {
  EMPTY_ITEM,
  itemErrors,
  ItemsField,
  itemsTotal,
  MAX_ITEMS,
} from "@/components/ItemsField";
import { LoadError, Loading } from "@/components/LoadState";
import { SelectField } from "@/components/SelectField";
import { TextareaField } from "@/components/TextareaField";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/api/errors";
import { useCreateBill, useProperties } from "@/lib/api/queries";
import { formatPesos } from "@/lib/format";
import { item, paymentDetails } from "@/lib/validation";

const FORM_ID = "bill";
const TITLE = "Nueva cuenta de cobro";

const schema = z.object({
  lease_id: z.string().min(1, "Elige a quién le cobras."),
  items: z.array(item).min(1).max(MAX_ITEMS),
  due_date: z.string().min(1, "Elige la fecha de vencimiento."),
  payment_details: paymentDetails,
});
type BillValues = z.infer<typeof schema>;

/** A manual bill: an extra charge on an active lease, apart from the monthly rent. */
export function NewBillScreen({ leaseId }: { leaseId?: string }) {
  const router = useRouter();
  const create = useCreateBill();
  const { data: properties, error: loadError, refetch } = useProperties();
  // Coming from a lease, go back to it.
  const back = leaseId ? `/leases/${leaseId}` : "/bills";
  const leases =
    properties?.flatMap((property) =>
      property.units.flatMap((unit) =>
        unit.active_lease
          ? [{ value: unit.active_lease.id, label: `${unit.name} · ${unit.active_lease.tenant_name}` }]
          : [],
      ),
    ) ?? [];

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<BillValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      lease_id: leaseId ?? "",
      items: [EMPTY_ITEM],
      due_date: "",
      payment_details: "",
    },
  });

  const total = itemsTotal(useWatch({ control, name: "items" }));

  if (!properties) {
    return (
      <FormScreenFallback title={TITLE} backHref={back}>
        {loadError ? (
          <LoadError message={errorMessage(loadError)} onRetry={refetch} />
        ) : (
          <Loading label="Cargando tus contratos" />
        )}
      </FormScreenFallback>
    );
  }

  if (leases.length === 0) {
    return (
      <FormScreenFallback title={TITLE} backHref={back}>
        <FormMessage tone="info">
          Una cuenta se genera sobre un contrato activo, y aún no tienes ninguno.
        </FormMessage>
        <Button asChild variant="outline" size="md">
          <Link href="/properties">Ir a mis inmuebles</Link>
        </Button>
      </FormScreenFallback>
    );
  }

  function submit(values: BillValues) {
    create.mutate(
      {
        body: {
          ...values,
          items: values.items.map((charged) => ({ ...charged, amount: charged.amount ?? 0 })),
          payment_details: values.payment_details || null,
        },
      },
      { onSuccess: (bill) => router.replace(`/bills/${bill.id}`) },
    );
  }

  return (
    <FormScreen
      title={TITLE}
      backHref={back}
      formId={FORM_ID}
      submitLabel="Generar cuenta"
      // Still "saving" after it worked: the screen is leaving and must not send it twice.
      saving={create.isPending || create.isSuccess}
      error={create.error ? errorMessage(create.error) : undefined}
    >
      <p className="text-support text-muted-foreground">
        Para un cobro aparte del canon, como un arreglo o un servicio. La cuenta del mes se genera
        desde el contrato.
      </p>
      <form
        id={FORM_ID}
        onSubmit={handleSubmit(submit)}
        noValidate
        className="flex flex-col gap-5"
      >
        <Controller
          control={control}
          name="lease_id"
          render={({ field }) => (
            <SelectField
              id="lease_id"
              label="Contrato"
              options={leases}
              value={field.value || undefined}
              onChange={field.onChange}
              placeholder="Elige un contrato"
              error={errors.lease_id?.message}
            />
          )}
        />
        <Controller
          control={control}
          name="items"
          render={({ field }) => (
            <ItemsField
              id="item"
              min={1}
              placeholder="Qué estás cobrando"
              addLabel="Agregar otro concepto"
              value={field.value}
              onChange={field.onChange}
              errors={itemErrors(errors.items)}
            />
          )}
        />
        <div className="flex items-baseline justify-between gap-3 rounded-xl border border-border bg-card p-4">
          <p className="text-section font-semibold">Total a pagar</p>
          <p className="text-title font-bold">{formatPesos(total)}</p>
        </div>
        <FormField
          id="due_date"
          label="Vence el"
          type="date"
          description="Una sola fecha para toda la cuenta."
          error={errors.due_date?.message}
          {...register("due_date")}
        />
        <TextareaField
          id="payment_details"
          label="Cómo te pagan (opcional)"
          placeholder="Banco, tipo y número de cuenta, Nequi…"
          description="Solo para esta cuenta. Si lo dejas vacío, se usan los del contrato o los de Ajustes."
          rows={3}
          error={errors.payment_details?.message}
          {...register("payment_details")}
        />
      </form>
    </FormScreen>
  );
}
