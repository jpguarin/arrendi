import { ChevronLeft } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";

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
    <header className="flex min-h-11 items-center gap-2 px-5 pt-6 pb-4">
      {backHref && (
        <Button asChild variant="ghost" size="icon" className="-ml-2.5 text-foreground">
          <Link href={backHref} aria-label="Volver">
            <ChevronLeft aria-hidden className="size-6" />
          </Link>
        </Button>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <h1 className={backHref ? "truncate text-title-back font-bold" : "text-title font-bold"}>
          {title}
        </h1>
        {subtitle && <p className="truncate text-support text-muted-foreground">{subtitle}</p>}
      </div>
      {children}
    </header>
  );
}
