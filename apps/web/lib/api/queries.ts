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
type Bill = Schemas["BillResponse"];
type BillSummary = Schemas["BillSummary"];
type Settings = Schemas["SettingsResponse"];
export type BillFilters = {
  unit_id?: string;
  status?: "receivable" | "paid" | "voided";
  /** Only the bills of this month and later (`2026-05-01`). */
  from?: string;
};

const ME = $api.queryOptions("get", "/api/me").queryKey;
const PROPERTIES = $api.queryOptions("get", "/api/properties").queryKey;
const leaseKey = (leaseId: string) =>
  $api.queryOptions("get", "/api/leases/{lease_id}", { params: { path: { lease_id: leaseId } } })
    .queryKey;

// Every month of the home screen.
const SUMMARIES = ["get", "/api/summary"] as const;
const SETTINGS = $api.queryOptions("get", "/api/settings").queryKey;
const SIGNATURE = $api.queryOptions("get", "/api/settings/signature").queryKey;
// Every list of bills, whatever its filters: the key of each one starts like this.
const BILL_LISTS = ["get", "/api/bills"] as const;
const billKey = (billId: string) =>
  $api.queryOptions("get", "/api/bills/{bill_id}", { params: { path: { bill_id: billId } } })
    .queryKey;

// Reads

export const useMe = () => $api.useQuery("get", "/api/me");

export const useProperties = () => $api.useQuery("get", "/api/properties");

export const useLease = (leaseId: string) =>
  $api.useQuery("get", "/api/leases/{lease_id}", { params: { path: { lease_id: leaseId } } });

/** The home screen: the figures of the current month and who owes what. */
export const useSummary = () => $api.useQuery("get", "/api/summary");

export const useSettings = () => $api.useQuery("get", "/api/settings");
// A temporary link to the owner's signature. It lasts five minutes, so it is asked for
// again before that.
const SIGNATURE_LINK_MS = 4 * 60 * 1000;
export const useSignatureUrl = (enabled: boolean) =>
  $api.useQuery(
    "get",
    "/api/settings/signature",
    {},
    { enabled, staleTime: SIGNATURE_LINK_MS, refetchInterval: SIGNATURE_LINK_MS },
  );

/** The bills that match the filters. Without a status, voided ones are left out. */
export const useBills = (filters: BillFilters = {}) =>
  $api.useQuery("get", "/api/bills", { params: { query: filters } });

export const useBill = (billId: string) =>
  $api.useQuery("get", "/api/bills/{bill_id}", { params: { path: { bill_id: billId } } });

// What a write leaves in memory. The answer of the API goes straight in, so the next
// screen shows the change at once.

/**
 * Marks data as old. What is on screen right now is asked for again at once: a list
 * stays in view next to the detail that made the change. The rest waits until a screen
 * that shows it opens.
 */
function markStale(client: QueryClient, queryKey: readonly unknown[]) {
  client.invalidateQueries({ queryKey });
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

function putBill(client: QueryClient, bill: Bill) {
  client.setQueryData<Bill>(billKey(bill.id), bill);
  // Its row in every list changes right away; the lists are then asked for again,
  // because a filter may no longer include it.
  client.setQueriesData<BillSummary[]>({ queryKey: BILL_LISTS }, (list) =>
    list?.map((old) =>
      old.id !== bill.id
        ? old
        : {
            ...old,
            status: bill.status,
            total: bill.total,
            balance: bill.balance,
            last_payment_date: bill.last_payment_date,
            last_payment_method: bill.last_payment_method,
          },
    ),
  );
  markStale(client, BILL_LISTS);
  // A bill or a payment changes the figures of the home screen and how its unit is doing.
  markStale(client, SUMMARIES);
  markStale(client, PROPERTIES);
  // The lease shows its latest bills, and it may be the screen that is open right now.
  client.invalidateQueries({ queryKey: leaseKey(bill.lease_id) });
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

/** Issues the bill of the current month for a lease. */
export function useGenerateMonthlyBill() {
  const client = useQueryClient();
  return $api.useMutation("post", "/api/leases/{lease_id}/bills", {
    onSuccess: (bill) => putBill(client, bill),
  });
}

/** Issues a manual bill: an extra charge on a lease. */
export function useCreateBill() {
  const client = useQueryClient();
  return $api.useMutation("post", "/api/bills", {
    onSuccess: (bill) => putBill(client, bill),
  });
}

export function useVoidBill() {
  const client = useQueryClient();
  return $api.useMutation("post", "/api/bills/{bill_id}/void", {
    onSuccess: (bill) => putBill(client, bill),
  });
}

export function useUpdateSettings() {
  const client = useQueryClient();
  return $api.useMutation("patch", "/api/settings", {
    onSuccess: (settings) => {
      client.setQueryData<Settings>(SETTINGS, settings);
      // The home screen greets the owner by name.
      client.setQueryData<Me>(ME, (me) => me && { ...me, name: settings.name });
      // Each bill shows the owner's details as they are now.
      markStale(client, ["get", "/api/bills/{bill_id}"]);
    },
  });
}

// The email goes out right after the API answers, so the answer still says "pending".
// Asking again a moment later brings how it went.
const DELIVERY_WAIT_MS = 2500;

function putEmailedBill(client: QueryClient, bill: Bill) {
  putBill(client, bill);
  setTimeout(() => client.invalidateQueries({ queryKey: billKey(bill.id) }), DELIVERY_WAIT_MS);
}

/** Emails the bill to the tenant, or emails it again. */
export function useSendBill() {
  const client = useQueryClient();
  return $api.useMutation("post", "/api/bills/{bill_id}/send", {
    onSuccess: (bill) => putEmailedBill(client, bill),
  });
}

/** Emails the tenant a reminder of a bill that still has a balance. */
export function useRemindBill() {
  const client = useQueryClient();
  return $api.useMutation("post", "/api/bills/{bill_id}/remind", {
    onSuccess: (bill) => putEmailedBill(client, bill),
  });
}

/** Registers a payment on a bill. The receipt, if asked for, goes out right after. */
export function useRegisterPayment() {
  const client = useQueryClient();
  return $api.useMutation("post", "/api/bills/{bill_id}/payments", {
    onSuccess: (bill) => putEmailedBill(client, bill),
  });
}

/** Removes a payment entered by mistake. */
export function useDeletePayment() {
  const client = useQueryClient();
  return $api.useMutation("delete", "/api/payments/{payment_id}", {
    onSuccess: (bill) => putBill(client, bill),
  });
}

/** Asks for a bill again, after a proof of payment went up outside these hooks. */
export function useRefreshBill(billId: string) {
  const client = useQueryClient();
  return useCallback(
    () => client.invalidateQueries({ queryKey: billKey(billId) }),
    [client, billId],
  );
}

/** Asks for the settings again, after a signature went up outside these hooks. */
export function useRefreshSignature() {
  const client = useQueryClient();
  return useCallback(
    () =>
      Promise.all([
        client.invalidateQueries({ queryKey: SETTINGS }),
        client.invalidateQueries({ queryKey: SIGNATURE }),
      ]),
    [client],
  );
}

/** Takes the owner's signature away. The bills already issued keep theirs. */
export function useDeleteSignature() {
  const client = useQueryClient();
  return $api.useMutation("delete", "/api/settings/signature", {
    onSuccess: (settings) => {
      client.setQueryData<Settings>(SETTINGS, settings);
      client.removeQueries({ queryKey: SIGNATURE });
    },
  });
}
