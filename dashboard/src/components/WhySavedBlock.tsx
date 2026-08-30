import { cn, eyebrow } from "@/lib/ui";

/**
 * WHY — the hero line of the whole product. On a card it sits in its own quiet
 * panel so the eye lands on it after the title; on the detail page it is the
 * largest text on screen. Never small grey type.
 */
export function WhySavedBlock({
  whySaved,
  variant = "card",
  className,
}: {
  whySaved: string;
  variant?: "card" | "hero";
  className?: string;
}) {
  const hero = variant === "hero";

  return (
    <div
      className={cn(
        hero ? null : "rounded-lg bg-ink-850/80 px-3.5 py-3",
        className,
      )}
    >
      <p className={cn(eyebrow, "mb-1.5")}>Why you saved it</p>
      <p
        className={cn(
          "text-balance font-medium text-fog-50",
          hero ? "text-xl leading-snug sm:text-[26px]" : "text-[15px] leading-snug",
        )}
      >
        {whySaved}
      </p>
    </div>
  );
}
