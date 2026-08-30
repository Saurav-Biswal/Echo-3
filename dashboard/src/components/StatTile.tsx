import Link from "next/link";

import { cn, eyebrow, surface } from "@/lib/ui";

interface StatTileProps {
  label: string;
  value: number;
  /** One-line explanation of what the number means, in Echo's voice. */
  caption: string;
  href?: string;
  accentClassName?: string;
  emphasis?: boolean;
}

/** One number on the Overview header. Links through to the filtered list. */
export function StatTile({
  label,
  value,
  caption,
  href,
  accentClassName = "bg-fog-600",
  emphasis = false,
}: StatTileProps) {
  const body = (
    <>
      <span className={cn("absolute inset-y-4 left-0 w-[2px] rounded-full", accentClassName)} />
      <span className={eyebrow}>{label}</span>
      <span
        className={cn(
          "block font-mono text-3xl leading-none tracking-tight",
          emphasis && value > 0 ? "text-fog-50" : "text-fog-100",
        )}
      >
        {value}
      </span>
      <span className="block text-[12px] leading-snug text-fog-500">{caption}</span>
    </>
  );

  const shell = cn(
    surface,
    "relative block space-y-2.5 p-5 transition-colors",
    href ? "hover:border-fog-600" : null,
  );

  if (!href) return <div className={shell}>{body}</div>;

  return (
    <Link href={href} className={shell}>
      {body}
    </Link>
  );
}
