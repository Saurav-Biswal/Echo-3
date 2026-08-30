import { cn, eyebrow } from "@/lib/ui";
import type { ReactNode } from "react";

/** Standard page masthead: eyebrow, title, one line of Echo's voice. */
export function PageHeader({
  label,
  title,
  lede,
  aside,
  className,
}: {
  label?: string;
  title: ReactNode;
  lede?: string;
  aside?: ReactNode;
  className?: string;
}) {
  return (
    <header className={cn("flex flex-wrap items-end justify-between gap-4", className)}>
      <div className="min-w-0 space-y-2">
        {label ? <p className={eyebrow}>{label}</p> : null}
        <h1 className="text-2xl leading-tight font-semibold tracking-tight text-fog-50 sm:text-[28px]">
          {title}
        </h1>
        {lede ? (
          <p className="max-w-2xl text-sm leading-relaxed text-fog-400">{lede}</p>
        ) : null}
      </div>
      {aside ? <div className="shrink-0">{aside}</div> : null}
    </header>
  );
}
