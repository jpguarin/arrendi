import { cn } from "@/lib/utils";

// The house of the isotipo (the same path as BrandMark), with its four windows off.
const WINDOWS = [
  { x: 78, y: 86, delay: "delay-500" },
  { x: 107, y: 86, delay: "delay-800" },
  { x: 78, y: 115, delay: "delay-1100" },
  { x: 107, y: 115, delay: "delay-1400" },
];

/**
 * The drawing of the not-found page. On arrival the windows are lit, as in the logo, and
 * go out one by one; with reduced motion they do not fade, but go out in the same order.
 */
export function EmptyHouse({ className }: { className?: string }) {
  return (
    <svg aria-hidden viewBox="14 2 180 148" className={cn("h-auto w-60 md:w-80", className)}>
      <path
        className="fill-foreground"
        d="M159.5 130.5V81.7208L103.559 39.463L48.5 81.6612V130.5C48.5 137.956 42.4558 144 35 144C27.5442 144 21.5 137.956 21.5 130.5V75.0001C21.5 70.8004 23.4548 66.84 26.7881 64.2853L95.2881 11.7853L95.7451 11.4493C100.521 8.09516 106.945 8.18407 111.637 11.7276L181.137 64.2276C184.514 66.779 186.5 70.7673 186.5 75.0001V130.5C186.5 137.956 180.456 144 173 144C165.544 144 159.5 137.956 159.5 130.5Z"
      />
      {WINDOWS.map(({ x, y, delay }) => (
        <rect
          key={`${x}-${y}`}
          x={x}
          y={y}
          width="23"
          height="23"
          rx="5"
          strokeWidth="2"
          strokeDasharray="5 4"
          className={cn("fill-muted stroke-border-dashed animate-window-off motion-reduce:animation-duration-1", delay)}
        />
      ))}
    </svg>
  );
}
