import { cn } from "@/lib/utils";

type FormMessageProps = {
  tone: "error" | "success" | "info";
  children: React.ReactNode;
};

/** A message about the whole form: what went wrong, or what happens next. */
export function FormMessage({ tone, children }: FormMessageProps) {
  return (
    <p
      role={tone === "error" ? "alert" : "status"}
      className={cn(
        "rounded-lg px-3.5 py-3 text-support",
        tone === "error" && "bg-alert-tint text-alert-ink",
        tone === "success" && "bg-positive-tint text-positive-ink",
        // Something the owner should know that is not a problem.
        tone === "info" && "bg-info-tint text-info-ink",
      )}
    >
      {children}
    </p>
  );
}
