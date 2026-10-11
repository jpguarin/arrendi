"use client";

import { Button } from "@/components/ui/button";

export function RetryButton() {
  return (
    <Button className="w-full" onClick={() => window.location.reload()}>
      Reintentar
    </Button>
  );
}
