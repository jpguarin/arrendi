"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useCallback } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/FormField";
import { FormScreen, FormScreenFallback } from "@/components/FormScreen";
import { LoadError, Loading } from "@/components/LoadState";
import { SelectField } from "@/components/SelectField";
import { api } from "@/lib/api/client";
import { useLoad } from "@/lib/api/useLoad";
import { useSave } from "@/lib/api/useSave";
import { UNIT_USE_OPTIONS } from "@/lib/labels";
import { requiredText } from "@/lib/validation";

const FORM_ID = "unit";
const BACK = "/properties";

const schema = z.object({
  name: requiredText("Escribe el nombre de la unidad."),
  use: z.enum(["residential", "commercial"]),
});
type Values = z.infer<typeof schema>;

function UnitForm({
  defaultValues,
  onSubmit,
}: {
  defaultValues?: Values;
  onSubmit: (values: Values) => void | Promise<void>;
}) {
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: defaultValues ?? { name: "", use: "residential" },
  });

  return (
    <form id={FORM_ID} onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-5">
      <FormField
        id="name"
        label="Nombre de la unidad"
        placeholder="Apto 1"
        description="Cada espacio que cobras por separado es una unidad."
        autoComplete="off"
        error={errors.name?.message}
        {...register("name")}
      />
      <Controller
        control={control}
        name="use"
        render={({ field }) => (
          <SelectField
            id="use"
            label="Uso"
            options={UNIT_USE_OPTIONS}
            value={field.value}
            onChange={field.onChange}
          />
        )}
      />
    </form>
  );
}

function useProperties() {
  // The API has no route for one property or one unit; the list is short.
  const load = useCallback(() => api.GET("/api/properties"), []);
  return useLoad(load);
}

function useDone() {
  const router = useRouter();
  return useCallback(() => {
    router.replace(BACK);
    router.refresh();
  }, [router]);
}

export function NewUnitScreen({ propertyId }: { propertyId: string }) {
  const done = useDone();
  const { save, saving, error } = useSave();
  const { data: properties, error: loadError, reload } = useProperties();
  const property = properties?.find((candidate) => candidate.id === propertyId);

  if (!property) {
    return (
      <FormScreenFallback title="Nueva unidad" backHref={BACK}>
        {loadError ? (
          <LoadError message={loadError} onRetry={reload} />
        ) : properties ? (
          <LoadError message="No encontramos este inmueble." onRetry={reload} />
        ) : (
          <Loading label="Cargando el inmueble" />
        )}
      </FormScreenFallback>
    );
  }

  async function onSubmit(values: Values) {
    const saved = await save(() =>
      api.POST("/api/properties/{property_id}/units", {
        params: { path: { property_id: propertyId } },
        body: values,
      }),
    );
    if (saved) done();
  }

  return (
    <FormScreen
      title="Nueva unidad"
      subtitle={property.name}
      backHref={BACK}
      formId={FORM_ID}
      submitLabel="Agregar unidad"
      saving={saving}
      error={error}
    >
      <UnitForm onSubmit={onSubmit} />
    </FormScreen>
  );
}

export function EditUnitScreen({ unitId }: { unitId: string }) {
  const done = useDone();
  const { save, saving, error } = useSave();
  const { data: properties, error: loadError, reload } = useProperties();
  const property = properties?.find((candidate) =>
    candidate.units.some((unit) => unit.id === unitId),
  );
  const unit = property?.units.find((candidate) => candidate.id === unitId);

  if (!property || !unit) {
    return (
      <FormScreenFallback title="Editar unidad" backHref={BACK}>
        {loadError ? (
          <LoadError message={loadError} onRetry={reload} />
        ) : properties ? (
          <LoadError message="No encontramos esta unidad." onRetry={reload} />
        ) : (
          <Loading label="Cargando la unidad" />
        )}
      </FormScreenFallback>
    );
  }

  async function onSubmit(values: Values) {
    const saved = await save(() =>
      api.PATCH("/api/units/{unit_id}", { params: { path: { unit_id: unitId } }, body: values }),
    );
    if (saved) done();
  }

  return (
    <FormScreen
      title="Editar unidad"
      subtitle={property.name}
      backHref={BACK}
      formId={FORM_ID}
      submitLabel="Guardar cambios"
      saving={saving}
      error={error}
    >
      <UnitForm defaultValues={{ name: unit.name, use: unit.use }} onSubmit={onSubmit} />
    </FormScreen>
  );
}
