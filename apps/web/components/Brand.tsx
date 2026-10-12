import { cn } from "@/lib/utils";

/**
 * The isotipo of docs/new-brand-design/arrendi-logo.svg. The house takes the text color,
 * so it reads on any surface; the windows stay brand green.
 */
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg aria-hidden viewBox="18 6 172 142" className={cn("h-7 w-auto shrink-0", className)}>
      <g fill="currentColor">
        <rect x="137" y="12" width="28" height="50" rx="6" />
        <path d="M159.5 130.5V81.72L103.56 39.46 48.5 81.66V130.5a13.5 13.5 0 0 1-27 0V75a13.5 13.5 0 0 1 5.29-10.71l68.5-52.5.46-.34a13.5 13.5 0 0 1 15.89.28l69.5 52.5A13.5 13.5 0 0 1 186.5 75v55.5a13.5 13.5 0 0 1-27 0Z" />
      </g>
      <g className="fill-brand-green">
        <rect x="77" y="85" width="25" height="25" rx="5.5" />
        <rect x="106" y="85" width="25" height="25" rx="5.5" />
        <rect x="77" y="114" width="25" height="25" rx="5.5" />
        <rect x="106" y="114" width="25" height="25" rx="5.5" />
      </g>
    </svg>
  );
}

/** The isotipo with the name next to it. */
export function Brand({ className }: { className?: string }) {
  return (
    <p className={cn("flex items-center gap-2 font-heading text-title-back font-black tracking-tight", className)}>
      <BrandMark />
      Arrendi
    </p>
  );
}
