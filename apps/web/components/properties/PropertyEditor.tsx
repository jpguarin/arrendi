"use client";

import { useRouter } from "next/navigation";

import { FormScreen, FormScreenFallback } from "@/components/FormScreen";
import { LoadError, Loading } from "@/components/LoadState";
import { PropertyForm, type PropertyValues } from "@/components/properties/PropertyForm";
import { errorMessage } from "@/lib/api/errors";
import { useCreateProperty, useProperties, useUpdateProperty } from "@/lib/api/queries";

const FORM_ID = "property";
const BACK = "/properties";

export function NewPropertyScreen() {
  const router = useRouter();
  const create = useCreateProperty();

  return (
    <FormScreen
      title="Nuevo inmueble"
      backHref={BACK}
      formId={FORM_ID}
      submitLabel="Crear inmueble"
      // Still "saving" after it worked: the screen is leaving and must not send it twice.
      saving={create.isPending || create.isSuccess}
      error={create.error ? errorMessage(create.error) : undefined}
    >
      <PropertyForm
        id={FORM_ID}
        onSubmit={(values: PropertyValues) =>
          create.mutate({ body: values }, { onSuccess: () => router.replace(BACK) })
        }
      />
    </FormScreen>
  );
}

export function EditPropertyScreen({ propertyId }: { propertyId: string }) {
  const router = useRouter();
  const update = useUpdateProperty();
  // The API has no route for one property; the list is short and usually in memory.
  const { data: properties, error, refetch } = useProperties();
  const property = properties?.find((candidate) => candidate.id === propertyId);

  if (!property) {
    return (
      <FormScreenFallback title="Editar inmueble" backHref={BACK}>
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
      title="Editar inmueble"
      subtitle={property.name}
      backHref={BACK}
      formId={FORM_ID}
      submitLabel="Guardar cambios"
      saving={update.isPending || update.isSuccess}
      error={update.error ? errorMessage(update.error) : undefined}
    >
      <PropertyForm
        id={FORM_ID}
        defaultValues={{
          name: property.name,
          address: property.address ?? "",
          city: property.city ?? "",
          type: property.type,
        }}
        onSubmit={(values: PropertyValues) =>
          update.mutate(
            { params: { path: { property_id: propertyId } }, body: values },
            { onSuccess: () => router.replace(BACK) },
          )
        }
      />
    </FormScreen>
  );
}
