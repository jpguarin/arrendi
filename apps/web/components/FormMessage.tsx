import { cn } from "@/lib/utils";

type FormMessageProps = {
  tone: "error" | "success";
  children: React.ReactNode;
};

/** A message about the whole form: what went wrong, or what happens next. */
export function FormMessage({ tone, children }: FormMessageProps) {
  return (
    <p
      role={tone === "error" ? "alert" : "status"}
      className={cn(
        "rounded-lg px-3.5 py-3 text-support",
        tone === "error" ? "bg-alert-tint text-alert" : "bg-primary-tint text-primary-strong",
      )}
    >
      {children}
    </p>
  );
}
