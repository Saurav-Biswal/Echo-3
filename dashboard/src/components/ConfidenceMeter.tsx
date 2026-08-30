import { CONFIDENCE_LABEL } from "@/lib/format";
import type { ConfidenceBand } from "@/lib/types";
import { cn } from "@/lib/ui";

const BAND_STEPS: Record<ConfidenceBand, number> = { LOW: 1, MEDIUM: 2, HIGH: 3 };

const BAND_COLOR: Record<ConfidenceBand, string> = {
  LOW: "bg-fog-500",
  MEDIUM: "bg-event",
  HIGH: "bg-recipe",
};

/**
 * Confidence, honestly but quietly: three steps and a word, never a percentage
 * shouted on every card. The exact score stays in the title attribute.
 */
export function ConfidenceMeter({
  band,
  score,
  showLabel = true,
  className,
}: {
  band: ConfidenceBand;
  score: number;
  showLabel?: boolean;
  className?: string;
}) {
  const steps = BAND_STEPS[band];
  const pct = Math.round(Math.min(Math.max(score, 0), 1) * 100);

  return (
    <span
      className={cn("inline-flex items-center gap-2", className)}
      title={`Echo's confidence: ${band} (${pct}%)`}
    >
      <span className="flex items-end gap-[3px]" aria-hidden="true">
        {[1, 2, 3].map((step) => (
          <span
            key={step}
            className={cn(
              "w-[3px] rounded-full",
              step === 1 ? "h-[6px]" : step === 2 ? "h-[9px]" : "h-[12px]",
              step <= steps ? BAND_COLOR[band] : "bg-ink-700",
            )}
          />
        ))}
      </span>
      <span className="sr-only">{`Echo's confidence: ${band}`}</span>
      {showLabel ? (
        <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-fog-500">
          {CONFIDENCE_LABEL[band]}
        </span>
      ) : null}
    </span>
  );
}
