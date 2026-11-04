import { cn } from "@/lib/utils";

/**
 * The CargoHaven mark: a vessel at rest inside a protected harbour. The ring is the harbour's
 * security perimeter, open at its entrance, with a beacon on each breakwater end.
 * The same drawing is used for public/favicon.svg and the marketing site.
 */
export function BrandMark({ className }: { className?: string | undefined }) {
  return (
    <svg
      viewBox="0 0 32 32"
      aria-hidden="true"
      focusable="false"
      fill="none"
      strokeLinecap="round"
      className={cn("size-5", className)}
    >
      <path d="M6.91 11.25A10.5 10.5 0 1 0 14.18 6.16" className="stroke-signal" strokeWidth="2" />
      <circle cx="6.91" cy="11.25" r="1.6" className="fill-brand-teal" />
      <circle cx="14.18" cy="6.16" r="1.6" className="fill-brand-teal" />
      <path d="M10.5 17.25h11l-2 3.3h-7Z" className="fill-foreground" />
      <path d="M17.4 13.9h2.6v3.35h-2.6Z" className="fill-foreground" />
      <path d="M10 22.9h12" className="stroke-signal/60" strokeWidth="1.5" />
    </svg>
  );
}

/** The CargoHaven wordmark with its mark, for the app header and sign-in screen. */
export function BrandLockup({ subtitle }: { subtitle?: string | undefined }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex size-7 shrink-0 items-center justify-center rounded-sm bg-signal/10 ring-1 ring-signal/35">
        <BrandMark />
      </div>
      <div className="leading-none">
        <div className="text-sm font-semibold tracking-[0.18em]">CARGOHAVEN</div>
        {subtitle ? <div className="label-mono text-[9px]">{subtitle}</div> : null}
      </div>
    </div>
  );
}
