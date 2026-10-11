"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/FormField";
import { FieldError, FieldLegend, FieldSet } from "@/components/ui/field";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { PROPERTY_TYPE_OPTIONS, type PropertyType } from "@/lib/labels";
import { optionalText, requiredText } from "@/lib/validation";

const schema = z.object({
  name: requiredText("Escribe un nombre para el inmueble."),
  address: optionalText,
  city: optionalText,
  type: z.enum(["house", "building", "apartment", "shop"], "Elige el tipo de inmueble."),
});
export type PropertyValues = z.infer<typeof schema>;

type PropertyFormProps = {
  /** The submit button lives in the screen's footer and points here with `form`. */
  id: string;
  defaultValues?: Partial<PropertyValues>;
  onSubmit: (values: PropertyValues) => void | Promise<void>;
};

/** Name, address, city and type of a property. Used by the onboarding and by Inmuebles. */
export function PropertyForm({ id, defaultValues, onSubmit }: PropertyFormProps) {
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<PropertyValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", address: "", city: "", ...defaultValues },
  });

  return (
    <form id={id} onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-5">
      <FormField
        id="name"
        label="Nombre del inmueble"
        description="Un nombre corto para reconocerlo."
        autoComplete="off"
        error={errors.name?.message}
        {...register("name")}
      />
      <FormField
        id="address"
        label="Dirección"
        placeholder="Calle, número y barrio"
        autoComplete="street-address"
        error={errors.address?.message}
        {...register("address")}
      />
      <FormField
        id="city"
        label="Ciudad"
        autoComplete="address-level2"
        error={errors.city?.message}
        {...register("city")}
      />
      <FieldSet data-invalid={Boolean(errors.type)}>
        <FieldLegend variant="label">Tipo</FieldLegend>
        <Controller
          control={control}
          name="type"
          render={({ field }) => (
            <ToggleGroup
              type="single"
              className="grid-cols-2"
              value={field.value ?? ""}
              // Tapping the selected option again would clear it; keep it selected.
              onValueChange={(value) => value && field.onChange(value as PropertyType)}
              aria-describedby={errors.type ? "type-error" : undefined}
            >
              {PROPERTY_TYPE_OPTIONS.map((option) => (
                <ToggleGroupItem key={option.value} value={option.value}>
                  {option.label}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          )}
        />
        {errors.type && <FieldError id="type-error">{errors.type.message}</FieldError>}
      </FieldSet>
    </form>
  );
}
