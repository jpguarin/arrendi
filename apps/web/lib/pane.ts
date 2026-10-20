// The width of the detail panel next to a list, when the owner drags its edge.
// Without a width of their own, the panel keeps the one of the design (360 or 408 px).

export const PANE_MIN = 360;
export const PANE_MAX = 720;
/** What the list keeps at least, so its rows still read. */
const LIST_MIN = 360;
const STEP = 16;
const BIG_STEP = 64;

export const PANE_STORAGE_KEY = "arrendi:pane-width";

export type PaneLimits = { min: number; max: number };

/** How narrow and how wide the panel can be, in a layout this wide. */
export function paneLimits(containerWidth: number): PaneLimits {
  return { min: PANE_MIN, max: Math.max(PANE_MIN, Math.min(PANE_MAX, containerWidth - LIST_MIN)) };
}

export function clampPaneWidth(width: number, limits: PaneLimits): number {
  return Math.round(Math.min(limits.max, Math.max(limits.min, width)));
}

/** The width after a key on the edge, or undefined if the key does not move it. */
export function stepPaneWidth(
  width: number,
  key: string,
  shift: boolean,
  limits: PaneLimits,
): number | undefined {
  const step = shift ? BIG_STEP : STEP;
  // The panel is on the right: moving its edge to the left widens it.
  if (key === "ArrowLeft") return clampPaneWidth(width + step, limits);
  if (key === "ArrowRight") return clampPaneWidth(width - step, limits);
  if (key === "Home") return limits.min;
  if (key === "End") return limits.max;
  return undefined;
}

/** The width saved in this browser, if it is one the panel could have. */
export function parseStoredWidth(value: string | null): number | null {
  if (!value || !/^\d+$/.test(value)) return null;
  const width = Number(value);
  return width >= PANE_MIN && width <= PANE_MAX ? width : null;
}
