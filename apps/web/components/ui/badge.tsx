import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

// A status, always said with text (docs/diseno.md). The tone only supports it.
const badgeVariants = cva(
  "inline-flex h-6 w-fit shrink-0 items-center justify-center rounded-sm px-2 text-badge font-semibold whitespace-nowrap",
  {
    variants: {
      tone: {
        // Pagada, Al día, Activo.
        positive: "bg-primary-tint text-primary-strong",
        // Vencida, En mora.
        alert: "bg-alert-tint text-alert",
        // Parcial.
        info: "bg-info-tint text-info",
        // Vacía, Terminado, Anulada.
        neutral: "bg-muted text-muted-foreground",
      },
    },
    defaultVariants: {
      tone: "neutral",
    },
  }
)

function Badge({
  className,
  tone = "neutral",
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return (
    <span
      data-slot="badge"
      data-tone={tone}
      className={cn(badgeVariants({ tone }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
