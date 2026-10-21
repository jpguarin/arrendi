"use client";

import { ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";

/** Goes back to the previous page; opened in a new tab, there is none, so it goes home. */
export function BackButton({ className }: { className?: string }) {
  const router = useRouter();
  return (
    <Button
      variant="outline"
      className={className}
      onClick={() => (window.history.length > 1 ? router.back() : router.push("/"))}
    >
      <ArrowLeft aria-hidden />
      Volver
    </Button>
  );
}
