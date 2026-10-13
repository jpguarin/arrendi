"use client";

import { Plus, X } from "lucide-react";
import { useState } from "react";
import type { FieldErrors } from "react-hook-form";

import { FormField } from "@/components/FormField";
import { MoneyField } from "@/components/MoneyField";
import { Button } from "@/components/ui/button";

/** Something charged, as the form holds it: the amount is null while its field is empty. */
export type ItemValue = { description: string; amount: number | null };
export type ItemErrors = ({ description?: string; amount?: string } | undefined)[];

/** A bill fits on one page with this many; the API refuses more. */
export const MAX_ITEMS = 10;
export const EMPTY_ITEM: ItemValue = { description: "", amount: null };

/** What the items add up to. The ones still without an amount count as zero. */
export const itemsTotal = (items: readonly ItemValue[]) =>
  items.reduce((sum, item) => sum + (item.amount ?? 0), 0);

/** The messages of each row, from what the form reports for its `items`. */
export function itemErrors(
  errors: FieldErrors<{ items: ItemValue[] }>["items"],
): ItemErrors | undefined {
  if (!Array.isArray(errors)) return undefined;
  return errors.map(
    (error) =>
      error && { description: error.description?.message, amount: error.amount?.message },
  );
}

type ItemsFieldProps = {
  /** Prefix of the ids of its fields, unique in the screen. */
  id: string;
  value: ItemValue[];
  onChange: (items: ItemValue[]) => void;
  errors?: ItemErrors;
  /** A manual bill charges at least one thing; a lease may charge nothing but the rent. */
  min?: number;
  placeholder?: string;
  addLabel?: string;
};

/** A list of things to charge, each with its own amount. The owner adds and removes rows. */
export function ItemsField({
  id,
  value,
  onChange,
  errors,
  min = 0,
  placeholder,
  addLabel = "Agregar concepto",
}: ItemsFieldProps) {
  // The items carry no id, so each row gets one here: taking a row out of the middle must
  // not hand its fields, and the focus in them, to the row that follows.
  const [rows, setRows] = useState<{ keys: (number | string)[]; next: number }>(() => ({
    keys: value.map((_, index) => index),
    next: value.length,
  }));
  // If the form replaced the list on its own, the ids no longer match it: go by position.
  const keyOf = (index: number) =>
    rows.keys.length === value.length ? rows.keys[index] : `at-${index}`;

  const change = (index: number, changes: Partial<ItemValue>) =>
    onChange(value.map((item, at) => (at === index ? { ...item, ...changes } : item)));
  const add = () => {
    setRows({ keys: [...value.map((_, index) => keyOf(index)), rows.next], next: rows.next + 1 });
    onChange([...value, EMPTY_ITEM]);
  };
  const remove = (index: number) => {
    setRows({ ...rows, keys: value.map((_, at) => keyOf(at)).filter((_, at) => at !== index) });
    onChange(value.filter((_, at) => at !== index));
  };
  // One row needs no number; with several, the number tells their labels apart.
  const numbered = value.length > 1;

  return (
    <div className="flex flex-col gap-2">
      {value.map((item, index) => {
        const suffix = numbered ? ` ${index + 1}` : "";
        return (
          <div
            key={keyOf(index)}
            className="flex flex-col gap-3 rounded-xl border border-border bg-card p-3"
          >
            <FormField
              id={`${id}-${index}-description`}
              label={`Concepto${suffix}`}
              placeholder={placeholder}
              autoComplete="off"
              value={item.description}
              onChange={(event) => change(index, { description: event.target.value })}
              error={errors?.[index]?.description}
            />
            <div className="flex items-start gap-2">
              <div className="min-w-0 flex-1">
                <MoneyField
                  id={`${id}-${index}-amount`}
                  label={`Valor${suffix}`}
                  placeholder="$0"
                  value={item.amount}
                  onChange={(amount) => change(index, { amount })}
                  error={errors?.[index]?.amount}
                />
              </div>
              {value.length > min && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  // Level with the field, below its label.
                  className="mt-7 -mr-1 text-muted-foreground"
                  aria-label={`Quitar concepto${suffix}`}
                  onClick={() => remove(index)}
                >
                  <X aria-hidden />
                </Button>
              )}
            </div>
          </div>
        );
      })}
      {value.length < MAX_ITEMS && (
        <Button
          type="button"
          variant="dashed"
          size="md"
          onClick={add}
        >
          <Plus aria-hidden />
          {addLabel}
        </Button>
      )}
    </div>
  );
}
