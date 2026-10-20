"use client";

import { usePathname } from "next/navigation";
import { createContext, useContext, useRef } from "react";

import { PaneResizer, usePaneWidth } from "@/components/shell/PaneResizer";
import { PANE_MIN } from "@/lib/pane";
import { cn } from "@/lib/utils";

// Whether the list is next to an open detail, which is then the main content.
const BesideDetail = createContext(false);

/**
 * A list and, when one of its things is open, its detail in a panel next to it. On a
 * phone the detail takes the whole screen.
 *
 * `root` is the path of the list alone; any other path under this layout is a detail.
 * From tablet up, the owner can drag the edge of the panel to change its width.
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
  const layout = useRef<HTMLDivElement>(null);
  const [width, setWidth] = usePaneWidth();

  return (
    <div
      ref={layout}
      // The owner's width, if any; the CSS keeps it from leaving the list too narrow when
      // the window is smaller than where it was chosen.
      style={
        width === null
          ? undefined
          : ({
              "--pane-width": `max(${PANE_MIN}px, min(${width}px, 100% - ${PANE_MIN}px))`,
            } as React.CSSProperties)
      }
      className={cn(
        "flex flex-1 flex-col md:grid md:min-h-dvh",
        open &&
          "md:grid-cols-[minmax(0,1fr)_var(--pane-width,22.5rem)] xl:grid-cols-[minmax(0,1fr)_var(--pane-width,var(--container-pane))]",
      )}
    >
      {/*
        Always the same element, so opening or closing a detail does not start the list
        over: its filters and its scroll stay. On a phone it hides behind the detail.
      */}
      <div
        role={open ? "region" : undefined}
        aria-label={open ? "Lista" : undefined}
        className={cn("flex min-w-0 flex-1 flex-col", open && "max-md:hidden")}
      >
        <BesideDetail value={open}>{list}</BesideDetail>
      </div>
      {open && (
        // The edge sits outside the scroll of the panel, which would clip it.
        <div className="relative flex min-w-0 flex-col md:sticky md:top-0 md:h-dvh">
          <PaneResizer container={layout} onChange={setWidth} />
          <div className="flex min-h-dvh min-w-0 flex-1 flex-col bg-card md:min-h-0 md:overflow-y-auto md:border-l md:border-border">
            {children}
          </div>
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
  return (
    <div
      role={beside ? undefined : "main"}
      className={cn("flex flex-1 flex-col gap-4 px-4 pb-8 md:px-6 xl:px-8", className)}
    >
      {children}
    </div>
  );
}
