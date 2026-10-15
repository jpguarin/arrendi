"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Controller, useFieldArray, useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { FieldError } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { UNIT_USE_OPTIONS } from "@/lib/labels";
import { requiredText } from "@/lib/validation";

import { useOnboarding } from "./OnboardingContext";

const FORM_ID = "onboarding-units";
// The API takes up to 50 in one go; more can be added later from Inmuebles.
const MAX_UNITS = 50;
const ERROR_ID = "units-error";
const ROW = "grid grid-cols-[minmax(0,1fr)_8.5rem_2.75rem] items-center gap-2 sm:grid-cols-[minmax(0,1fr)_9.5rem_2.75rem]";

const schema = z.object({
  units: z
    .array(
      z.object({
        name: requiredText("Escribe el nombre de la unidad."),
        use: z.enum(["residential", "commercial"]),
      }),
    )
    .min(1),
});
type Values = z.infer<typeof schema>;

/** Second part of the sheet: the units, as a small table of name and use. */
export function UnitsStep() {
  const router = useRouter();
  const { draft, update } = useOnboarding();
  // A shop is one commercial unit far more often than a home.
  const firstUse = draft.property?.type === "shop" ? "commercial" : "residential";
  const {
    register,
    control,
    handleSubmit,
    subscribe,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { units: draft.unitsInput ?? draft.units ?? [{ name: "", use: firstUse }] },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "units" });
  const missingName = errors.units?.some?.((unit) => unit?.name);

  useEffect(
    () =>
      subscribe({
        formState: { values: true },
        callback: ({ values }) => update({ unitsInput: values.units }),
      }),
    [subscribe, update],
  );

  return (
    <form
      id={FORM_ID}
      noValidate
      className="flex flex-col gap-4"
      onSubmit={handleSubmit(({ units }) => {
        // The lease may point at a unit that is no longer there.
        const unit = Number(draft.lease?.unit);
        const lease = unit < units.length ? draft.lease : { ...draft.lease, unit: "0" };
        update({ units, unitsInput: undefined, lease });
        router.push("/onboarding/lease");
      })}
    >
      <p className="-mt-1 text-support text-muted-foreground">
        Cada espacio que cobras por separado es una unidad.
      </p>
      <div role="table" aria-label="Unidades" className="overflow-hidden rounded-lg border border-border">
        <div role="row" className={`${ROW} bg-muted py-2 pr-1.5 pl-3.5 text-badge font-semibold text-muted-foreground`}>
          <span role="columnheader">Nombre</span>
          <span role="columnheader">Uso</span>
          <span role="columnheader">
            <span className="sr-only">Quitar</span>
          </span>
        </div>
        {fields.map((field, index) => {
          const invalid = Boolean(errors.units?.[index]?.name);
          return (
            <div key={field.id} role="row" className={`${ROW} border-t border-border py-1.5 pr-1.5 pl-1.5`}>
              <span role="cell" className="min-w-0">
                <label htmlFor={`unit-${index}`} className="sr-only">
                  Unidad {index + 1}
                </label>
                <Input
                  id={`unit-${index}`}
                  className="h-11 border-transparent bg-transparent hover:border-border"
                  placeholder={`Apto ${index + 1}`}
                  autoComplete="off"
                  aria-invalid={invalid}
                  aria-describedby={invalid ? ERROR_ID : undefined}
                  {...register(`units.${index}.name`)}
                />
              </span>
              <span role="cell">
                <Controller
                  control={control}
                  name={`units.${index}.use`}
                  render={({ field: use }) => (
                    <Select value={use.value} onValueChange={use.onChange}>
                      <SelectTrigger
                        className="h-11 px-3"
                        aria-label={`Uso de la unidad ${index + 1}`}
                      >
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {UNIT_USE_OPTIONS.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </span>
              <span role="cell">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="text-muted-foreground"
                  aria-label={`Quitar unidad ${index + 1}`}
                  // A property needs at least one unit.
                  disabled={fields.length === 1}
                  onClick={() => remove(index)}
                >
                  <X aria-hidden />
                </Button>
              </span>
            </div>
          );
        })}
      </div>
      {missingName && <FieldError id={ERROR_ID}>Escribe el nombre de cada unidad.</FieldError>}
      <div className="flex flex-wrap gap-2">
        {fields.length < MAX_UNITS && (
          <Button
            type="button"
            variant="dashed"
            size="md"
            onClick={() => append({ name: "", use: firstUse })}
          >
            <Plus aria-hidden />
            Agregar unidad
          </Button>
        )}
        <Button type="submit" size="md">
          Continuar
        </Button>
      </div>
    </form>
  );
}
