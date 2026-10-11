"use client";

import { SerwistProvider } from "@serwist/turbopack/react";

import { AppUpdate } from "@/components/AppUpdate";

/** Registers the service worker. Off in development, where it would serve stale files. */
export function PwaProvider({ children }: { children: React.ReactNode }) {
  return (
    <SerwistProvider swUrl="/serwist/sw.js" disable={process.env.NODE_ENV === "development"}>
      <AppUpdate />
      {children}
    </SerwistProvider>
  );
}
