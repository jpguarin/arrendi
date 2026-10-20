"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import {
  clampPaneWidth,
  PANE_MAX,
  PANE_MIN,
  PANE_STORAGE_KEY,
  paneLimits,
  parseStoredWidth,
  stepPaneWidth,
} from "@/lib/pane";

// Browser storage can be missing or blocked (private windows); the panel then just
// keeps the width of the design.
function save(width: number | null) {
  try {
    if (width === null) localStorage.removeItem(PANE_STORAGE_KEY);
    else localStorage.setItem(PANE_STORAGE_KEY, String(width));
  } catch {}
}

function stored(): number | null {
  try {
    return parseStoredWidth(localStorage.getItem(PANE_STORAGE_KEY));
  } catch {
    return null;
  }
}

// Another tab may change it; this one follows.
function subscribe(changed: () => void) {
  window.addEventListener("storage", changed);
  return () => window.removeEventListener("storage", changed);
}

/**
 * The width the owner gave the detail panel in this browser, or null for the one of the
 * design. The server does not know it, so the first drawing has the design's.
 */
export function usePaneWidth() {
  const saved = useSyncExternalStore(subscribe, stored, () => null);
  // What the owner did here, from the first move on; undefined until then.
  const [chosen, setChosen] = useState<number | null>();
  return [chosen === undefined ? saved : chosen, setChosen] as const;
}

// While dragging, the whole page shows the resize cursor and selects no text.
const DRAGGING = ["cursor-col-resize", "select-none"];

/**
 * The left edge of the detail panel, to make it wider or narrower: dragged with a mouse,
 * a pen or a finger, or moved with the arrows. A double click puts it back.
 *
 * It sits in the panel, which is inside `container`: the layout the list and the panel
 * share, whose width sets how wide the panel can get.
 */
export function PaneResizer({
  container,
  onChange,
}: {
  container: React.RefObject<HTMLElement | null>;
  onChange: (width: number | null) => void;
}) {
  const edge = useRef<HTMLDivElement>(null);
  const drag = useRef<{ x: number; width: number; last: number } | null>(null);
  const [dragging, setDragging] = useState(false);
  // What the panel and the layout measure now, for the screen reader.
  const [now, setNow] = useState({ width: PANE_MIN, max: PANE_MAX });

  const panelWidth = () => edge.current?.parentElement?.getBoundingClientRect().width ?? PANE_MIN;
  const limits = () => paneLimits(container.current?.getBoundingClientRect().width ?? 0);

  useEffect(() => {
    const panel = edge.current?.parentElement;
    const layout = container.current;
    if (!panel || !layout) return;
    const observer = new ResizeObserver(() =>
      setNow({ width: Math.round(panelWidth()), max: limits().max }),
    );
    observer.observe(panel);
    observer.observe(layout);
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [container]);

  function onPointerDown(event: React.PointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    const width = Math.round(panelWidth());
    drag.current = { x: event.clientX, width, last: width };
    setDragging(true);
    document.documentElement.classList.add(...DRAGGING);
  }

  function onPointerMove(event: React.PointerEvent<HTMLDivElement>) {
    if (!drag.current) return;
    // The panel is on the right: moving its edge to the left widens it.
    const width = clampPaneWidth(drag.current.width + drag.current.x - event.clientX, limits());
    drag.current.last = width;
    onChange(width);
  }

  function onPointerUp() {
    if (!drag.current) return;
    // A click without moving leaves the width as it was, of the design or not.
    if (drag.current.last !== drag.current.width) save(drag.current.last);
    drag.current = null;
    setDragging(false);
    document.documentElement.classList.remove(...DRAGGING);
  }

  function reset() {
    onChange(null);
    save(null);
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      reset();
      return;
    }
    const width = stepPaneWidth(Math.round(panelWidth()), event.key, event.shiftKey, limits());
    if (width === undefined) return;
    event.preventDefault();
    onChange(width);
    save(width);
  }

  return (
    <div
      ref={edge}
      role="separator"
      aria-orientation="vertical"
      aria-label="Ancho del panel"
      aria-valuemin={PANE_MIN}
      aria-valuemax={now.max}
      aria-valuenow={now.width}
      tabIndex={0}
      data-dragging={dragging || undefined}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onDoubleClick={reset}
      onKeyDown={onKeyDown}
      title="Arrastra para cambiar el ancho. Doble clic para volver al de siempre."
      className="group absolute inset-y-0 left-0 z-10 w-11 -translate-x-1/2 cursor-col-resize touch-none outline-none max-md:hidden"
    >
      <span
        aria-hidden
        className="absolute inset-y-0 left-1/2 w-0.5 -translate-x-1/2 bg-transparent transition-colors group-hover:bg-primary group-focus-visible:bg-primary group-data-dragging:bg-primary"
      />
    </div>
  );
}
