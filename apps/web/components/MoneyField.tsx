"use client";

import { FormField } from "@/components/FormField";
import { formatPesos, parsePesos } from "@/lib/format";

type MoneyFieldProps = Omit<
  React.ComponentProps<typeof FormField>,
  "value" | "onChange" | "type" | "inputMode"
> & {
  /** Whole pesos, or null while the field is empty. */
  value: number | null;
  onChange: (value: number | null) => void;
};

// Longer than any rent, and far below the point where a number loses precision.
const MAX_DIGITS = 12;

/** A field for whole pesos. It shows `$950.000` while the owner types only digits. */
export function MoneyField({ value, onChange, ...fieldProps }: MoneyFieldProps) {
  return (
    <FormField
      {...fieldProps}
      type="text"
      inputMode="numeric"
      autoComplete="off"
      value={value === null ? "" : formatPesos(value)}
      onChange={(event) => {
        const digits = event.target.value.replace(/\D/g, "").slice(0, MAX_DIGITS);
        onChange(parsePesos(digits));
      }}
    />
  );
}
