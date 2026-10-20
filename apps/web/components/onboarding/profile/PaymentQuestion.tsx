"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { FormField } from "@/components/FormField";
import { TextareaField } from "@/components/TextareaField";
import { Button } from "@/components/ui/button";
import { FieldError, FieldLegend, FieldSet } from "@/components/ui/field";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { errorMessage } from "@/lib/api/errors";
import { useUpdateSettings } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { DOCUMENT_TYPE_LABELS } from "@/lib/labels";
import {
  ACCOUNT_TYPES,
  type AccountType,
  BANKS,
  composePaymentDetails,
  isWallet,
  type PaymentAccount,
} from "@/lib/payment-details";
import { paymentDetails } from "@/lib/validation";

import { QuestionFrame } from "./QuestionFrame";
import { nextStep, profileHref } from "./steps";

type Settings = components["schemas"]["SettingsResponse"];
type Problems = { bank?: string; number?: string; text?: string };

/**
 * How the owner gets paid. The bank and the number are tapped and typed; the text the
 * tenant reads writes itself. "Prefiero escribirlo yo" leaves a free text, as in Ajustes,
 * and is where an answer already saved opens, since its pieces are not kept.
 */
export function PaymentQuestion({ settings }: { settings: Settings }) {
  const router = useRouter();
  const update = useUpdateSettings();
  const [byHand, setByHand] = useState(Boolean(settings.payment_details));
  const [text, setText] = useState(settings.payment_details ?? "");
  const [account, setAccount] = useState<PaymentAccount>({
    bank: "",
    otherBank: "",
    type: "Ahorros",
    number: "",
  });
  const [problems, setProblems] = useState<Problems>({});

  const written = composePaymentDetails(account, {
    name: settings.name,
    document: settings.document_number
      ? `${DOCUMENT_TYPE_LABELS[settings.document_type]} ${settings.document_number}`
      : "",
  });
  const wallet = isWallet(account.bank);

  function change(changes: Partial<PaymentAccount>) {
    setAccount((current) => ({ ...current, ...changes }));
    setProblems({});
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    let found: Problems = {};
    if (byHand) {
      const checked = paymentDetails.safeParse(text);
      if (!checked.success) found = { text: checked.error.issues[0].message };
      else if (!checked.data) found = { text: "Cuéntale a tu arrendatario cómo pagarte." };
    } else if (!account.bank) {
      found = { bank: "Elige dónde te consignan." };
    } else if (!account.number.trim()) {
      found = { number: wallet ? "Escribe el celular." : "Escribe el número de la cuenta." };
    }
    setProblems(found);
    if (Object.keys(found).length) return;
    update.mutate(
      { body: { payment_details: byHand ? text.trim() : written } },
      { onSuccess: () => router.push(profileHref(nextStep("payment"))) },
    );
  }

  return (
    <QuestionFrame
      question="payment"
      title="¿Cómo te pagan tus arrendatarios?"
      description={
        byHand
          ? "Escríbelo como quieres que lo lean en la cuenta."
          : "Toca tu banco; escribimos el texto por ti."
      }
      saving={update.isPending}
      error={update.error ? errorMessage(update.error) : undefined}
      onSubmit={submit}
    >
      {byHand ? (
        <>
          <TextareaField
            id="payment_details"
            label="Cómo te pagan"
            placeholder="Banco, tipo y número de cuenta, Nequi…"
            description="Aparece en cada cuenta de cobro, después de “Pagar a:”."
            rows={4}
            value={text}
            onChange={(event) => {
              setText(event.target.value);
              setProblems({});
            }}
            error={problems.text}
          />
          <Button
            type="button"
            variant="link"
            className="self-start px-0"
            onClick={() => {
              setByHand(false);
              setProblems({});
            }}
          >
            Mejor elegir el banco
          </Button>
        </>
      ) : (
        <>
          <FieldSet data-invalid={Boolean(problems.bank)}>
            <FieldLegend variant="label">¿Dónde te consignan?</FieldLegend>
            <ToggleGroup
              type="single"
              className="grid-cols-3 sm:grid-cols-4"
              value={account.bank}
              onValueChange={(bank) => bank && change({ bank })}
              aria-describedby={problems.bank ? "bank-error" : undefined}
            >
              {BANKS.map((bank) => (
                <ToggleGroupItem
                  key={bank}
                  value={bank}
                  className="h-auto min-h-13 px-2 text-center text-section leading-tight whitespace-normal"
                >
                  {bank}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
            {problems.bank && <FieldError id="bank-error">{problems.bank}</FieldError>}
          </FieldSet>
          {account.bank === "Otro" && (
            <FormField
              id="other_bank"
              label="Nombre del banco"
              autoComplete="off"
              value={account.otherBank}
              onChange={(event) => change({ otherBank: event.target.value })}
            />
          )}
          {account.bank && (
            // The kind of account and its number: one under the other on a phone.
            <div className={wallet ? "flex flex-col" : "grid gap-5 sm:grid-cols-2 sm:gap-3"}>
              {!wallet && (
                <FieldSet>
                  <FieldLegend variant="label">Tipo de cuenta</FieldLegend>
                  <ToggleGroup
                    type="single"
                    className="grid-cols-2"
                    value={account.type}
                    onValueChange={(type) => type && change({ type: type as AccountType })}
                  >
                    {ACCOUNT_TYPES.map((type) => (
                      <ToggleGroupItem key={type} value={type}>
                        {type}
                      </ToggleGroupItem>
                    ))}
                  </ToggleGroup>
                </FieldSet>
              )}
              <FormField
                id="account_number"
                label={wallet ? "Celular" : "Número de cuenta"}
                inputMode="numeric"
                autoComplete="off"
                value={account.number}
                onChange={(event) => change({ number: event.target.value })}
                error={problems.number}
              />
            </div>
          )}
          {written && (
            <div className="flex flex-col gap-1 rounded-xl bg-muted px-3.5 py-3">
              <p className="text-badge font-semibold text-muted-foreground">
                Así lo leerá tu arrendatario
              </p>
              <p className="text-section whitespace-pre-line">{written}</p>
            </div>
          )}
          <Button
            type="button"
            variant="link"
            className="self-start px-0"
            onClick={() => {
              setByHand(true);
              if (written) setText(written);
              setProblems({});
            }}
          >
            Prefiero escribirlo yo (efectivo, otra forma…)
          </Button>
        </>
      )}
    </QuestionFrame>
  );
}
