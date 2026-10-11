import { FormMessage } from "@/components/FormMessage";
import { Button } from "@/components/ui/button";

/** Placeholder blocks while a screen's data arrives. */
export function Loading({ label }: { label: string }) {
  return (
    <div role="status" aria-label={label} className="flex flex-col gap-4">
      <div className="h-44 animate-pulse rounded-xl bg-muted" />
      <div className="h-13 animate-pulse rounded-lg bg-muted" />
    </div>
  );
}

/** What went wrong loading a screen, with a way to try again. */
export function LoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col gap-4">
      <FormMessage tone="error">{message}</FormMessage>
      <Button variant="outline" size="md" onClick={onRetry}>
        Reintentar
      </Button>
    </div>
  );
}
