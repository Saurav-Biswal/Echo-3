import type { MemoryStatus, NotificationStatus } from "@/lib/types";
import { cn } from "@/lib/ui";

const MEMORY_STATUS: Record<MemoryStatus, { label: string; tone: string }> = {
  ACTIVE: { label: "Waiting", tone: "text-fog-300 border-line" },
  RESURFACED: {
    label: "Resurfaced",
    tone: "text-accent border-[color:color-mix(in_srgb,var(--color-accent)_45%,transparent)]",
  },
  COMPLETED: { label: "Done", tone: "text-recipe border-[#22453a]" },
  DISMISSED: { label: "Dismissed", tone: "text-fog-500 border-line-soft" },
  ARCHIVED: { label: "Archived", tone: "text-fog-500 border-line-soft" },
  NEEDS_REVIEW: { label: "Needs review", tone: "text-event border-[#4d3a1f]" },
};

const NOTIFICATION_STATUS: Record<NotificationStatus, { label: string; tone: string }> = {
  SCHEDULED: { label: "Scheduled", tone: "text-fog-300 border-line" },
  SENT: { label: "Sent", tone: "text-place border-[#1f3a4d]" },
  ACTED: { label: "Acted", tone: "text-recipe border-[#22453a]" },
  DISMISSED: { label: "Dismissed", tone: "text-fog-500 border-line-soft" },
};

const shell =
  "inline-flex items-center rounded-full border bg-ink-900/60 px-2 py-0.5 " +
  "font-mono text-[10px] uppercase tracking-[0.16em]";

/** Lifecycle state of a memory, in plain words rather than the enum name. */
export function StatusPill({
  status,
  className,
}: {
  status: MemoryStatus;
  className?: string;
}) {
  const { label, tone } = MEMORY_STATUS[status];
  return <span className={cn(shell, tone, className)}>{label}</span>;
}

/** The same treatment for a notification in the resurfacing feed. */
export function NotificationStatusPill({
  status,
  className,
}: {
  status: NotificationStatus;
  className?: string;
}) {
  const { label, tone } = NOTIFICATION_STATUS[status];
  return <span className={cn(shell, tone, className)}>{label}</span>;
}
