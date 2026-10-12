"use client";

import { usePathname } from "next/navigation";
import { createContext, useContext } from "react";

import { cn } from "@/lib/utils";

// Whether the list is next to an open detail, which is then the main content.
const BesideDetail = createContext(false);

/**
 * A list and, when one of its things is open, its detail in a panel next to it. On a
 * phone the detail takes the whole screen.
 *
 * `root` is the path of the list alone; any other path under this layout is a detail.
 */
export function ListDetail({
  root,
  list,
  children,
}: {
  root: string;
  list: React.ReactNode;
  children: React.ReactNode;
}) {
  const open = usePathname() !== root;

  return (
    <div
      className={cn(
        "flex flex-1 flex-col md:grid md:min-h-dvh",
        open && "md:grid-cols-[minmax(0,1fr)_22.5rem] xl:grid-cols-[minmax(0,1fr)_var(--container-pane)]",
      )}
    >
      {open ? (
        <section aria-label="Lista" className="flex min-w-0 flex-col max-md:hidden">
          <BesideDetail value={true}>{list}</BesideDetail>
        </section>
      ) : (
        <div className="flex min-w-0 flex-1 flex-col">{list}</div>
      )}
      {open && (
        <div className="flex min-h-dvh min-w-0 flex-col bg-card md:sticky md:top-0 md:h-dvh md:min-h-0 md:overflow-y-auto md:border-l md:border-border">
          {children}
        </div>
      )}
    </div>
  );
}

/**
 * The body of a list screen. It is the main content of the page, except when a detail
 * is open next to it.
 */
export function ListMain({ className, children }: { className?: string; children: React.ReactNode }) {
  const beside = useContext(BesideDetail);
  const Tag = beside ? "div" : "main";
  return (
    <Tag className={cn("flex flex-1 flex-col gap-4 px-4 pb-8 md:px-6 xl:px-8", className)}>
      {children}
    </Tag>
  );
}
