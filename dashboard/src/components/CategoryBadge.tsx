import { CATEGORY_META } from "@/lib/categories";
import type { Category } from "@/lib/types";
import { cn } from "@/lib/ui";

interface CategoryBadgeProps {
  category: Category;
  /** `chip` for cards, `hero` for the detail header. */
  size?: "chip" | "hero";
  className?: string;
}

/**
 * Category glyph + name. The colour comes from `--cat`, which globals.css sets
 * from the `data-category` attribute, so this stays a single generic component.
 */
export function CategoryBadge({
  category,
  size = "chip",
  className,
}: CategoryBadgeProps) {
  const meta = CATEGORY_META[category];
  const hero = size === "hero";

  return (
    <span
      data-category={category}
      className={cn(
        "inline-flex items-center gap-2 rounded-full border font-mono uppercase",
        "border-[color:color-mix(in_srgb,var(--cat)_35%,transparent)]",
        "bg-[color-mix(in_srgb,var(--cat)_10%,transparent)]",
        "text-[color:var(--cat)]",
        hero
          ? "px-3 py-1.5 text-[11px] tracking-[0.22em]"
          : "px-2.5 py-1 text-[10px] tracking-[0.18em]",
        className,
      )}
    >
      <span aria-hidden="true" className="text-[13px] leading-none">
        {meta.glyph}
      </span>
      {meta.label}
    </span>
  );
}
