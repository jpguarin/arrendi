"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Controller, useFieldArray, useForm } from "react-hook-form";
import { z } from "zod";

import { OnboardingScreen } from "@/components/onboarding/OnboardingScreen";
import { Button } from "@/components/ui/button";
import { FieldError } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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

export function UnitsStep() {
  const router = useRouter();
  const { draft, update } = useOnboarding();
  const {
    register,
    control,
    handleSubmit,
    getValues,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { units: draft.units ?? [{ name: "", use: "residential" }] },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "units" });

  // The steps keep their answers in memory: after a reload there is no property to add
  // units to, so start over.
  useEffect(() => {
    if (!draft.property) router.replace("/onboarding/property");
  }, [draft.property, router]);
  if (!draft.property) return null;

  return (
    <OnboardingScreen
      step={2}
      title={`¿Qué espacios arriendas en ${draft.property.name}?`}
      description="Cada espacio que cobras por separado es una unidad."
      footer={
        <div className="grid grid-cols-[1fr_2fr] gap-2">
          <Button asChild variant="outline">
            {/* Keeps what is typed so far, so going back does not lose it. */}
            <Link href="/onboarding/property" onClick={() => update({ units: getValues("units") })}>
              Atrás
            </Link>
          </Button>
          <Button type="submit" form={FORM_ID}>
            Continuar
          </Button>
        </div>
      }
    >
      <form
        id={FORM_ID}
        noValidate
        className="flex flex-col gap-2.5"
        onSubmit={handleSubmit(({ units }) => {
          // The lease may point at a unit that is no longer there.
          update({ units, lease: undefined });
          router.push("/onboarding/lease");
        })}
      >
        {fields.map((field, index) => {
          const error = errors.units?.[index]?.name?.message;
          return (
            <div
              key={field.id}
              className="flex flex-col gap-2 rounded-xl border border-border bg-card p-3"
            >
              <div className="flex items-end gap-2">
                <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                  <Label htmlFor={`unit-${index}`} className="text-badge text-muted-foreground">
                    Unidad {index + 1}
                  </Label>
                  <Input
                    id={`unit-${index}`}
                    className="h-11"
                    placeholder="Apto 1"
                    autoComplete="off"
                    aria-invalid={Boolean(error)}
                    aria-describedby={error ? `unit-${index}-error` : undefined}
                    {...register(`units.${index}.name`)}
                  />
                </div>
                <div className="flex w-32 flex-col gap-1.5">
                  <Label htmlFor={`use-${index}`} className="text-badge text-muted-foreground">
                    Uso
                  </Label>
                  <Controller
                    control={control}
                    name={`units.${index}.use`}
                    render={({ field: use }) => (
                      <Select value={use.value} onValueChange={use.onChange}>
                        <SelectTrigger id={`use-${index}`} className="h-11 px-3">
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
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="-mr-1 text-muted-foreground"
                  aria-label={`Quitar unidad ${index + 1}`}
                  // An inmueble needs at least one unit.
                  disabled={fields.length === 1}
                  onClick={() => remove(index)}
                >
                  <X aria-hidden />
                </Button>
              </div>
              {error && <FieldError id={`unit-${index}-error`}>{error}</FieldError>}
            </div>
          );
        })}
        {fields.length < MAX_UNITS && (
          <Button
            type="button"
            variant="dashed"
            size="md"
            onClick={() => append({ name: "", use: "residential" })}
          >
            <Plus aria-hidden />
            Agregar otra unidad
          </Button>
        )}
      </form>
    </OnboardingScreen>
  );
}
