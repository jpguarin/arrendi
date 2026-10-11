"use client";

import { useRouter } from "next/navigation";
import { useCallback } from "react";

import { FormScreen, FormScreenFallback } from "@/components/FormScreen";
import { LoadError, Loading } from "@/components/LoadState";
import { PropertyForm, type PropertyValues } from "@/components/properties/PropertyForm";
import { api } from "@/lib/api/client";
import { useLoad } from "@/lib/api/useLoad";
import { useSave } from "@/lib/api/useSave";

const FORM_ID = "property";
const BACK = "/properties";

function useDone() {
  const router = useRouter();
  return useCallback(() => {
    router.replace(BACK);
    router.refresh();
  }, [router]);
}

export function NewPropertyScreen() {
  const done = useDone();
  const { save, saving, error } = useSave();

  async function onSubmit(values: PropertyValues) {
    if (await save(() => api.POST("/api/properties", { body: values }))) done();
  }

  return (
    <FormScreen
      title="Nuevo inmueble"
      backHref={BACK}
      formId={FORM_ID}
      submitLabel="Crear inmueble"
      saving={saving}
      error={error}
    >
      <PropertyForm id={FORM_ID} onSubmit={onSubmit} />
    </FormScreen>
  );
}

export function EditPropertyScreen({ propertyId }: { propertyId: string }) {
  const done = useDone();
  const { save, saving, error } = useSave();
  // The API has no route for one property; the list is short.
  const load = useCallback(() => api.GET("/api/properties"), []);
  const { data: properties, error: loadError, reload } = useLoad(load);
  const property = properties?.find((candidate) => candidate.id === propertyId);

  if (!property) {
    return (
      <FormScreenFallback title="Editar inmueble" backHref={BACK}>
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

  async function onSubmit(values: PropertyValues) {
    const saved = await save(() =>
      api.PATCH("/api/properties/{property_id}", {
        params: { path: { property_id: propertyId } },
        body: values,
      }),
    );
    if (saved) done();
  }

  return (
    <FormScreen
      title="Editar inmueble"
      subtitle={property.name}
      backHref={BACK}
      formId={FORM_ID}
      submitLabel="Guardar cambios"
      saving={saving}
      error={error}
    >
      <PropertyForm
        id={FORM_ID}
        defaultValues={{
          name: property.name,
          address: property.address ?? "",
          city: property.city ?? "",
          type: property.type,
        }}
        onSubmit={onSubmit}
      />
    </FormScreen>
  );
}
