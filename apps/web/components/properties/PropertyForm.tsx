"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/FormField";
import { SelectField } from "@/components/SelectField";
import { FieldError, FieldLegend, FieldSet } from "@/components/ui/field";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { COUNTRY_OPTIONS, type Country, DEFAULT_COUNTRY } from "@/lib/countries";
import { PROPERTY_TYPE_OPTIONS, type PropertyType } from "@/lib/labels";
import { optionalText, requiredText } from "@/lib/validation";

const schema = z.object({
  name: requiredText("Escribe un nombre para el inmueble."),
  address: optionalText,
  city: optionalText,
  // Any code of the list; the API checks it again.
  country: z.custom<Country>((value) => COUNTRY_OPTIONS.some((option) => option.value === value), {
    message: "Elige el país.",
  }),
  type: z.enum(["house", "building", "apartment", "shop"], "Elige el tipo de inmueble."),
});
export type PropertyValues = z.infer<typeof schema>;

type PropertyFormProps = {
  /** The submit button lives in the screen's footer and points here with `form`. */
  id: string;
  defaultValues?: Partial<PropertyValues>;
  onSubmit: (values: PropertyValues) => void | Promise<void>;
  /** Called with what is typed, as it is typed: the onboarding keeps it as a draft. */
  onValuesChange?: (values: Partial<PropertyValues>) => void;
};

/** Name, address, city, country and type of a property. Used by the onboarding and by Inmuebles. */
export function PropertyForm({ id, defaultValues, onSubmit, onValuesChange }: PropertyFormProps) {
  const {
    register,
    control,
    handleSubmit,
    subscribe,
    formState: { errors },
  } = useForm<PropertyValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", address: "", city: "", country: DEFAULT_COUNTRY, ...defaultValues },
  });

  useEffect(() => {
    if (!onValuesChange) return;
    return subscribe({ formState: { values: true }, callback: ({ values }) => onValuesChange(values) });
  }, [subscribe, onValuesChange]);

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
      <Controller
        control={control}
        name="country"
        render={({ field }) => (
          <SelectField
            id="country"
            label="País"
            options={COUNTRY_OPTIONS}
            value={field.value}
            onChange={field.onChange}
            error={errors.country?.message}
          />
        )}
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
