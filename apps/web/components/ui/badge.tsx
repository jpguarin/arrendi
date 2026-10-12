import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

// A status, always said with text (docs/diseno.md). The tone only supports it.
const badgeVariants = cva(
  "inline-flex h-6 w-fit shrink-0 items-center justify-center gap-1 rounded-full px-2 text-badge font-semibold whitespace-nowrap [&_svg]:size-3.5 [&_svg]:shrink-0",
  {
    variants: {
      tone: {
        // Pagada, Al día, Activo.
        positive: "bg-positive-tint text-positive-ink",
        // Vencida, En mora.
        alert: "bg-alert-tint text-alert-ink",
        // Parcial, Pago parcial.
        warning: "bg-warning-tint text-warning-ink",
        // Pendiente.
        info: "bg-info-tint text-info-ink",
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
