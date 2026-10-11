"use client";

import { type QueryClient, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import { $api } from "./client";
import type { components } from "./schema";

// Every read and write of the app, in one place: what each write changes in the data
// kept in memory is decided here and not in the screens.

type Schemas = components["schemas"];
type Me = Schemas["MeResponse"];
type Property = Schemas["PropertyResponse"];
type Unit = Schemas["UnitResponse"];
type Lease = Schemas["LeaseResponse"];

const ME = $api.queryOptions("get", "/api/me").queryKey;
const PROPERTIES = $api.queryOptions("get", "/api/properties").queryKey;
const leaseKey = (leaseId: string) =>
  $api.queryOptions("get", "/api/leases/{lease_id}", { params: { path: { lease_id: leaseId } } })
    .queryKey;

// Reads

export const useMe = () => $api.useQuery("get", "/api/me");

export const useProperties = () => $api.useQuery("get", "/api/properties");

export const useLease = (leaseId: string) =>
  $api.useQuery("get", "/api/leases/{lease_id}", { params: { path: { lease_id: leaseId } } });

// What a write leaves in memory. The answer of the API goes straight in, so the next
// screen shows the change at once.

/**
 * Marks data as old without asking for it right now: the screen that shows it asks
 * when it opens. Asking here too would send the request twice, because the screen that
 * made the change is about to close and its request would be cancelled.
 */
function markStale(client: QueryClient, queryKey: readonly unknown[]) {
  client.invalidateQueries({ queryKey, refetchType: "none" });
}

function putProperty(client: QueryClient, property: Property) {
  client.setQueryData<Property[]>(PROPERTIES, (list) =>
    list?.some((old) => old.id === property.id)
      ? list.map((old) => (old.id === property.id ? property : old))
      : list && [...list, property],
  );
  markStale(client, PROPERTIES);
  // The first property completes the onboarding.
  markStale(client, ME);
}

function putUnit(client: QueryClient, unit: Unit) {
  client.setQueryData<Property[]>(PROPERTIES, (list) =>
    list?.map((property) =>
      property.id !== unit.property_id
        ? property
        : {
            ...property,
            units: property.units.some((old) => old.id === unit.id)
              ? property.units.map((old) => (old.id === unit.id ? unit : old))
              : [...property.units, unit],
          },
    ),
  );
  markStale(client, PROPERTIES);
}

function putLease(client: QueryClient, lease: Lease) {
  client.setQueryData<Lease>(leaseKey(lease.id), lease);
  // The list of properties shows each unit's active lease.
  client.setQueryData<Property[]>(PROPERTIES, (list) =>
    list?.map((property) => ({
      ...property,
      units: property.units.map((unit): Unit => {
        if (unit.id !== lease.unit.id) return unit;
        if (lease.status === "active") {
          const active_lease = { id: lease.id, tenant_name: lease.tenant.name, rent: lease.rent };
          return { ...unit, status: "up_to_date", active_lease };
        }
        return unit.active_lease?.id === lease.id
          ? { ...unit, status: "vacant", active_lease: null }
          : unit;
      }),
    })),
  );
  markStale(client, PROPERTIES);
}

// Writes

export function useCreateProperty() {
  const client = useQueryClient();
  return $api.useMutation("post", "/api/properties", {
    onSuccess: (property) => putProperty(client, property),
  });
}

export function useUpdateProperty() {
  const client = useQueryClient();
  return $api.useMutation("patch", "/api/properties/{property_id}", {
    onSuccess: (property) => putProperty(client, property),
  });
}

export function useAddUnit() {
  const client = useQueryClient();
  return $api.useMutation("post", "/api/properties/{property_id}/units", {
    onSuccess: (unit) => putUnit(client, unit),
  });
}

export function useUpdateUnit() {
  const client = useQueryClient();
  return $api.useMutation("patch", "/api/units/{unit_id}", {
    onSuccess: (unit) => putUnit(client, unit),
  });
}

export function useCreateLease() {
  const client = useQueryClient();
  return $api.useMutation("post", "/api/leases", {
    onSuccess: (lease) => putLease(client, lease),
  });
}

export function useUpdateLease() {
  const client = useQueryClient();
  return $api.useMutation("patch", "/api/leases/{lease_id}", {
    onSuccess: (lease) => putLease(client, lease),
  });
}

export function useEndLease() {
  const client = useQueryClient();
  return $api.useMutation("post", "/api/leases/{lease_id}/end", {
    onSuccess: (lease) => putLease(client, lease),
  });
}

export function useOnboard() {
  const client = useQueryClient();
  return $api.useMutation("post", "/api/onboarding", {
    onSuccess: ({ lease }) => {
      if (lease) client.setQueryData<Lease>(leaseKey(lease.id), lease);
      markStale(client, PROPERTIES);
    },
  });
}

/**
 * Marks the onboarding as done in memory. Called when leaving it, not when the API
 * answers: the last step may still have something to tell the owner.
 */
export function useMarkOnboarded() {
  const client = useQueryClient();
  return useCallback(() => {
    client.setQueryData<Me>(ME, (me) => me && { ...me, onboarding_complete: true });
    markStale(client, ME);
  }, [client]);
}

/** Asks for a lease again, after its document changed outside these hooks. */
export function useRefreshLease(leaseId: string) {
  const client = useQueryClient();
  return useCallback(
    () => client.invalidateQueries({ queryKey: leaseKey(leaseId) }),
    [client, leaseId],
  );
}
