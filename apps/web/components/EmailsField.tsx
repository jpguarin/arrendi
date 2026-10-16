"use client";

import { Plus, X } from "lucide-react";
import { useState } from "react";
import type { FieldErrors } from "react-hook-form";

import { FormField } from "@/components/FormField";
import { Button } from "@/components/ui/button";

/** A lease sends its emails in copy to this many addresses at most; the API refuses more. */
export const MAX_CC_EMAILS = 3;

/** The message of each row, from what the form reports for the list. */
export function emailErrors(
  errors: FieldErrors<{ emails: string[] }>["emails"],
): (string | undefined)[] | undefined {
  if (!Array.isArray(errors)) return undefined;
  return errors.map((error) => error?.message);
}

type EmailsFieldProps = {
  /** Prefix of the ids of its fields, unique in the screen. */
  id: string;
  value: string[];
  onChange: (emails: string[]) => void;
  errors?: (string | undefined)[];
};

/** A short list of email addresses. The owner adds and removes rows. */
export function EmailsField({ id, value, onChange, errors }: EmailsFieldProps) {
  // Each row gets its own id here: taking one out of the middle must not hand its field,
  // and the focus in it, to the row that follows.
  const [rows, setRows] = useState<{ keys: (number | string)[]; next: number }>(() => ({
    keys: value.map((_, index) => index),
    next: value.length,
  }));
  // If the form replaced the list on its own, the ids no longer match it: go by position.
  const keyOf = (index: number) =>
    rows.keys.length === value.length ? rows.keys[index] : `at-${index}`;

  const add = () => {
    setRows({ keys: [...value.map((_, index) => keyOf(index)), rows.next], next: rows.next + 1 });
    onChange([...value, ""]);
  };
  const remove = (index: number) => {
    setRows({ ...rows, keys: value.map((_, at) => keyOf(at)).filter((_, at) => at !== index) });
    onChange(value.filter((_, at) => at !== index));
  };
  // One row needs no number; with several, the number tells their labels apart.
  const numbered = value.length > 1;

  return (
    <div className="flex flex-col gap-2">
      {value.map((address, index) => {
        const suffix = numbered ? ` ${index + 1}` : "";
        return (
          <div key={keyOf(index)} className="flex items-start gap-2">
            <div className="min-w-0 flex-1">
              <FormField
                id={`${id}-${index}`}
                label={`Correo en copia${suffix}`}
                type="email"
                inputMode="email"
                autoComplete="off"
                autoCapitalize="none"
                value={address}
                onChange={(event) =>
                  onChange(value.map((current, at) => (at === index ? event.target.value : current)))
                }
                error={errors?.[index]}
              />
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              // Level with the field, below its label.
              className="mt-7 -mr-1 text-muted-foreground"
              aria-label={`Quitar correo en copia${suffix}`}
              onClick={() => remove(index)}
            >
              <X aria-hidden />
            </Button>
          </div>
        );
      })}
      {value.length < MAX_CC_EMAILS && (
        <Button type="button" variant="dashed" size="md" onClick={add}>
          <Plus aria-hidden />
          Agregar correo en copia
        </Button>
      )}
    </div>
  );
}
