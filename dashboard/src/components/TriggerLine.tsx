import { describeTrigger } from "@/lib/format";
import type { MemoryRead, TriggerType } from "@/lib/types";
import { cn } from "@/lib/ui";

const TRIGGER_GLYPH: Record<TriggerType, string> = {
  LOCATION: "◎",
  DATE: "◔",
  TIME: "◔",
  MANUAL: "◇",
};

/**
 * WHEN — the resurfacing trigger in human words. Server-authored `reason` is
 * used verbatim; the date, countdown or radius trails behind it.
 */
export function TriggerLine({
  memory,
  className,
}: {
  memory: MemoryRead;
  className?: string;
}) {
  const { headline, detail } = describeTrigger(memory);
  const trigger = memory.triggers[0] ?? null;
  const glyph = trigger ? TRIGGER_GLYPH[trigger.trigger_type] : TRIGGER_GLYPH.MANUAL;

  return (
    <p
      className={cn(
        "flex items-baseline gap-2 text-[13px] leading-snug text-fog-300",
        className,
      )}
    >
      <span aria-hidden="true" className="text-fog-500">
        {glyph}
      </span>
      <span>
        {headline}
        {detail ? (
          <span className="ml-2 font-mono text-[11px] uppercase tracking-[0.12em] text-fog-500">
            {detail}
          </span>
        ) : null}
      </span>
    </p>
  );
}
