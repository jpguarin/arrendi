"use client";

import { useSerwist } from "@serwist/turbopack/react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

/** Tells the owner a new version is ready, and reloads into it when they accept. */
export function AppUpdate() {
  const { serwist } = useSerwist();
  const [waiting, setWaiting] = useState(false);

  useEffect(() => {
    if (!serwist) return;
    const onWaiting = () => setWaiting(true);
    const onControlling = () => window.location.reload();
    serwist.addEventListener("waiting", onWaiting);
    serwist.addEventListener("controlling", onControlling);
    return () => {
      serwist.removeEventListener("waiting", onWaiting);
      serwist.removeEventListener("controlling", onControlling);
    };
  }, [serwist]);

  if (!waiting) return null;

  return (
    <div
      role="status"
      className="fixed inset-x-0 bottom-0 z-50 mx-auto flex w-full max-w-app items-center justify-between gap-3 border-t bg-card px-5 py-3"
    >
      <p className="text-support text-foreground">Hay una versión nueva de Arrendi.</p>
      <Button size="sm" onClick={() => serwist?.messageSkipWaiting()}>
        Actualizar
      </Button>
    </div>
  );
}
