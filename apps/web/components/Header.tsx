import { ChevronLeft } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type HeaderProps = {
  title: string;
  /** Second line under the title, like the property a unit belongs to. */
  subtitle?: string;
  /** Where the back button goes. Without it, this is a top-level screen. */
  backHref?: string;
  /** On the right: an action or a status badge. */
  children?: React.ReactNode;
};

/** Top of a screen: the title, with a back button or an action on the right. */
export function Header({ title, subtitle, backHref, children }: HeaderProps) {
  return (
    <header
      className={cn(
        "flex min-h-11 items-center gap-2",
        // Next to a back button it heads a detail; alone, a whole section.
        backHref ? "px-5 pt-4 pb-3" : "flex-wrap px-4 pt-5 pb-4 md:px-6 md:pt-6 xl:px-8",
      )}
    >
      {backHref && (
        <Button asChild variant="ghost" size="icon" className="-ml-2.5 text-foreground">
          <Link href={backHref} aria-label="Volver">
            <ChevronLeft aria-hidden className="size-6" />
          </Link>
        </Button>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <h1 className={backHref ? "truncate text-title-back font-extrabold" : "text-title font-extrabold"}>
          {title}
        </h1>
        {subtitle && <p className="truncate text-support text-muted-foreground">{subtitle}</p>}
      </div>
      {children}
    </header>
  );
}
