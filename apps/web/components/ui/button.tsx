import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { Slot } from "radix-ui"

// Sizes follow docs/diseno.md: no button is shorter than the 44px touch target.
const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border border-transparent bg-clip-padding text-body font-semibold whitespace-nowrap transition-all outline-none select-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 active:not-aria-[haspopup]:translate-y-px disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-5",
  {
    variants: {
      variant: {
        // Main action of the screen.
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        // Secondary action: border on a surface.
        outline:
          "border-input bg-card text-foreground hover:bg-muted aria-expanded:bg-muted",
        // Add or upload something.
        dashed:
          "border-dashed border-border-dashed bg-transparent text-foreground hover:bg-muted",
        ghost: "text-primary hover:bg-muted aria-expanded:bg-muted",
        destructive: "bg-alert-tint text-alert hover:bg-alert-tint/80",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-13 px-5",
        md: "h-12 px-4",
        sm: "h-11 px-3 text-section",
        icon: "size-11 rounded-full",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
