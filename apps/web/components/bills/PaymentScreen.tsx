"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/FormField";
import { FormMessage } from "@/components/FormMessage";
import { FormScreen, FormScreenFallback } from "@/components/FormScreen";
import { LoadError, Loading } from "@/components/LoadState";
import { MoneyField } from "@/components/MoneyField";
import { DocumentPicker } from "@/components/leases/DocumentPicker";
import { FieldLegend, FieldSet } from "@/components/ui/field";
import { Switch } from "@/components/ui/switch";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { uploadPaymentProof } from "@/lib/api/documents";
import { errorMessage, hasCode } from "@/lib/api/errors";
import { useBill, useRefreshBill, useRegisterPayment } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { formatBillNumber, formatMonth, formatPesos, todayInBogota } from "@/lib/format";
import { PAYMENT_METHOD_OPTIONS, type PaymentMethod } from "@/lib/labels";

type Bill = components["schemas"]["BillResponse"];

const FORM_ID = "payment";
const TITLE = "Registrar pago";

const schema = z.object({
  amount: z
    .number("Escribe el valor recibido.")
    .nullable()
    .refine((value) => value !== null && value > 0, "Escribe el valor recibido."),
  payment_date: z.string().min(1, "Elige la fecha del pago."),
  method: z.enum(["transfer", "nequi", "cash", "other"]),
  send_receipt: z.boolean(),
});
type PaymentValues = z.infer<typeof schema>;

function PaymentForm({ bill, back }: { bill: Bill; back: string }) {
  const router = useRouter();
  const register = useRegisterPayment();
  const refreshBill = useRefreshBill(bill.id);
  const [proof, setProof] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const today = todayInBogota();
  const {
    control,
    register: field,
    handleSubmit,
    formState: { errors },
  } = useForm<PaymentValues>({
    resolver: zodResolver(schema),
    // The usual payment: the whole balance, today, by transfer, with a receipt.
    defaultValues: {
      amount: bill.balance,
      payment_date: today,
      method: "transfer",
      send_receipt: true,
    },
  });

  function submit(values: PaymentValues) {
    const before = new Set(bill.payments.map((payment) => payment.id));
    register.mutate(
      {
        params: { path: { bill_id: bill.id } },
        body: { ...values, amount: values.amount ?? 0 },
      },
      {
        onSuccess: async (updated) => {
          const payment = updated.payments.find((candidate) => !before.has(candidate.id));
          let failed = false;
          if (proof && payment) {
            setUploading(true);
            // The payment is saved either way; the proof can be attached again later.
            failed = Boolean(await uploadPaymentProof(payment.id, proof));
            if (!failed) await refreshBill();
          }
          router.replace(failed ? `/bills/${bill.id}?proof=failed` : back);
        },
      },
    );
  }

  const description = bill.period
    ? `Cuenta ${formatBillNumber(bill.number)} · ${formatMonth(bill.period).toLowerCase()}`
    : `Cuenta ${formatBillNumber(bill.number)}`;

  return (
    <FormScreen
      title={TITLE}
      backHref={back}
      formId={FORM_ID}
      submitLabel={uploading ? "Subiendo el comprobante…" : "Guardar pago"}
      // Still "saving" after it worked: the screen is leaving and must not send it twice.
      saving={register.isPending || register.isSuccess}
      error={register.error ? errorMessage(register.error) : undefined}
    >
      <section
        aria-label="Cuenta que se paga"
        className="flex items-center justify-between gap-3 rounded-xl border border-border bg-card p-4"
      >
        <div className="flex min-w-0 flex-col gap-0.5">
          <p className="truncate text-body font-semibold">
            {bill.unit_name} · {bill.tenant_name}
          </p>
          <p className="truncate text-support text-muted-foreground">{description}</p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-0.5">
          <p className="text-support text-muted-foreground">Saldo</p>
          <p className="text-title-back font-bold">{formatPesos(bill.balance)}</p>
        </div>
      </section>
      <form
        id={FORM_ID}
        onSubmit={handleSubmit(submit)}
        noValidate
        className="flex flex-col gap-5"
      >
        <Controller
          control={control}
          name="amount"
          render={({ field: amount }) => (
            <MoneyField
              id="amount"
              label="Valor recibido"
              placeholder="$0"
              description="Si es menor al saldo, la cuenta queda como parcial."
              value={amount.value}
              onChange={amount.onChange}
              onBlur={amount.onBlur}
              error={errors.amount?.message}
            />
          )}
        />
        <FormField
          id="payment_date"
          label="Fecha del pago"
          type="date"
          max={today}
          error={errors.payment_date?.message}
          {...field("payment_date")}
        />
        <FieldSet>
          <FieldLegend variant="label">Medio de pago</FieldLegend>
          <Controller
            control={control}
            name="method"
            render={({ field: method }) => (
              <ToggleGroup
                type="single"
                className="grid-cols-2"
                value={method.value}
                // Tapping the selected option again would clear it; keep it selected.
                onValueChange={(value) => value && method.onChange(value as PaymentMethod)}
              >
                {PAYMENT_METHOD_OPTIONS.map((option) => (
                  <ToggleGroupItem key={option.value} value={option.value}>
                    {option.label}
                  </ToggleGroupItem>
                ))}
              </ToggleGroup>
            )}
          />
        </FieldSet>
        <DocumentPicker
          file={proof}
          onChange={setProof}
          label="Adjuntar comprobante (opcional)"
        />
        <label className="flex min-h-11 items-center justify-between gap-3 rounded-xl border border-border bg-card p-4">
          <span className="text-section">Enviar recibo al arrendatario por correo</span>
          <Controller
            control={control}
            name="send_receipt"
            render={({ field: receipt }) => (
              <Switch checked={receipt.value} onCheckedChange={receipt.onChange} />
            )}
          />
        </label>
      </form>
    </FormScreen>
  );
}

/** Registers a payment on a bill in a few taps: everything comes filled in. */
export function PaymentScreen({ billId, fromHome }: { billId: string; fromHome: boolean }) {
  const { data: latest, error, refetch } = useBill(billId);
  // The bill as it was when the screen opened. Saving the payment changes it in memory,
  // and the form must stay as it is until it has finished and left.
  const [opened, setOpened] = useState<Bill>();
  if (latest && !opened) setOpened(latest);
  const bill = opened ?? latest;
  // Coming from the home screen, go back to it: that is where the owner was working.
  const back = fromHome ? "/" : `/bills/${billId}`;

  if (!bill) {
    return (
      <FormScreenFallback title={TITLE} backHref={back}>
        {hasCode(error, "not_found") ? (
          <FormMessage tone="error">No encontramos esta cuenta.</FormMessage>
        ) : error ? (
          <LoadError message={errorMessage(error)} onRetry={refetch} />
        ) : (
          <Loading label="Cargando la cuenta" />
        )}
      </FormScreenFallback>
    );
  }

  if (bill.status === "paid" || bill.status === "voided") {
    return (
      <FormScreenFallback title={TITLE} backHref={back}>
        <FormMessage tone="info">
          {bill.status === "paid"
            ? "Esta cuenta ya está pagada."
            : "Esta cuenta está anulada y no admite pagos."}
        </FormMessage>
      </FormScreenFallback>
    );
  }

  return <PaymentForm bill={bill} back={back} />;
}
