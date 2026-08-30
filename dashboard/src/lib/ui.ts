/** Tiny class-name joiner. Kept local so the app pulls in no UI dependency. */
export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

/** The one card/panel surface treatment, reused everywhere. */
export const surface =
  "rounded-xl border border-line bg-ink-900/70 backdrop-blur-[1px]";

/** Small mono eyebrow used for WHAT / WHY / WHEN labels and stat captions. */
export const eyebrow =
  "font-mono text-[10px] uppercase tracking-[0.2em] text-fog-500";

const btnBase =
  "inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium " +
  "transition-colors disabled:cursor-not-allowed disabled:opacity-45";

export const btnPrimary = cn(
  btnBase,
  "h-10 px-4 bg-accent text-white hover:bg-accent/85",
);

export const btnSecondary = cn(
  btnBase,
  "h-10 px-4 border border-line bg-ink-800 text-fog-100 hover:border-fog-600 hover:bg-ink-700",
);

export const btnGhost = cn(
  btnBase,
  "h-9 px-3 text-fog-400 hover:bg-ink-800 hover:text-fog-100",
);

export const btnChip = cn(
  btnBase,
  "h-8 px-3 rounded-full border border-line text-xs text-fog-300 hover:border-fog-500 hover:text-fog-50",
);

export const btnDanger = cn(
  btnBase,
  "h-9 px-3 text-[#ff8080] hover:bg-[#2a1418] hover:text-[#ffb3b3]",
);
