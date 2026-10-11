"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/FormField";
import { FormScreen, FormScreenFallback } from "@/components/FormScreen";
import { LoadError, Loading } from "@/components/LoadState";
import { SelectField } from "@/components/SelectField";
import { errorMessage } from "@/lib/api/errors";
import { useAddUnit, useProperties, useUpdateUnit } from "@/lib/api/queries";
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

export function NewUnitScreen({ propertyId }: { propertyId: string }) {
  const router = useRouter();
  const add = useAddUnit();
  // The API has no route for one property; the list is short and usually in memory.
  const { data: properties, error, refetch } = useProperties();
  const property = properties?.find((candidate) => candidate.id === propertyId);

  if (!property) {
    return (
      <FormScreenFallback title="Nueva unidad" backHref={BACK}>
        {properties ? (
          <LoadError message="No encontramos este inmueble." onRetry={refetch} />
        ) : error ? (
          <LoadError message={errorMessage(error)} onRetry={refetch} />
        ) : (
          <Loading label="Cargando el inmueble" />
        )}
      </FormScreenFallback>
    );
  }

  return (
    <FormScreen
      title="Nueva unidad"
      subtitle={property.name}
      backHref={BACK}
      formId={FORM_ID}
      submitLabel="Agregar unidad"
      // Still "saving" after it worked: the screen is leaving and must not send it twice.
      saving={add.isPending || add.isSuccess}
      error={add.error ? errorMessage(add.error) : undefined}
    >
      <UnitForm
        onSubmit={(values) =>
          add.mutate(
            { params: { path: { property_id: propertyId } }, body: values },
            { onSuccess: () => router.replace(BACK) },
          )
        }
      />
    </FormScreen>
  );
}

export function EditUnitScreen({ unitId }: { unitId: string }) {
  const router = useRouter();
  const update = useUpdateUnit();
  const { data: properties, error, refetch } = useProperties();
  const property = properties?.find((candidate) =>
    candidate.units.some((unit) => unit.id === unitId),
  );
  const unit = property?.units.find((candidate) => candidate.id === unitId);

  if (!property || !unit) {
    return (
      <FormScreenFallback title="Editar unidad" backHref={BACK}>
        {properties ? (
          <LoadError message="No encontramos esta unidad." onRetry={refetch} />
        ) : error ? (
          <LoadError message={errorMessage(error)} onRetry={refetch} />
        ) : (
          <Loading label="Cargando la unidad" />
        )}
      </FormScreenFallback>
    );
  }

  return (
    <FormScreen
      title="Editar unidad"
      subtitle={property.name}
      backHref={BACK}
      formId={FORM_ID}
      submitLabel="Guardar cambios"
      saving={update.isPending || update.isSuccess}
      error={update.error ? errorMessage(update.error) : undefined}
    >
      <UnitForm
        defaultValues={{ name: unit.name, use: unit.use }}
        onSubmit={(values) =>
          update.mutate(
            { params: { path: { unit_id: unitId } }, body: values },
            { onSuccess: () => router.replace(BACK) },
          )
        }
      />
    </FormScreen>
  );
}
