import type {
  ConfidenceBand,
  EntityRead,
  IntentAction,
  MemoryRead,
  TriggerRead,
} from "@/lib/types";

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const;

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] as const;

/** Dates are formatted by hand so the output never drifts with the locale. */
export function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  // A bare `YYYY-MM-DD` (EntityRead.event_date) parses as UTC midnight, which
  // can slide a day backwards; pin it to local midnight instead.
  const bareDate = /^\d{4}-\d{2}-\d{2}$/.exec(value);
  if (bareDate) {
    const [y, m, d] = value.split("-").map(Number);
    return new Date(y, m - 1, d);
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function formatDay(value: string | null | undefined): string | null {
  const date = parseDate(value);
  if (!date) return null;
  return `${DAYS[date.getDay()]} ${date.getDate()} ${MONTHS[date.getMonth()]}`;
}

export function formatDateTime(value: string | null | undefined): string | null {
  const date = parseDate(value);
  if (!date) return null;
  const hh = String(date.getHours()).padStart(2, "0");
  const mm = String(date.getMinutes()).padStart(2, "0");
  return `${formatDay(value)} · ${hh}:${mm}`;
}

function startOfDay(date: Date): number {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
}

const DAY_MS = 86_400_000;

/** "tomorrow", "in 3 days", "in 4 hours", "2 days ago". Null when unparseable. */
export function countdown(
  value: string | null | undefined,
  now: Date = new Date(),
): string | null {
  const date = parseDate(value);
  if (!date) return null;

  const dayDelta = Math.round((startOfDay(date) - startOfDay(now)) / DAY_MS);
  if (dayDelta === 0) {
    const hours = Math.round((date.getTime() - now.getTime()) / 3_600_000);
    if (hours >= 2) return `in ${hours} hours`;
    if (hours === 1) return "in an hour";
    if (hours <= -2) return `${Math.abs(hours)} hours ago`;
    if (hours === -1) return "an hour ago";
    return "right now";
  }
  if (dayDelta === 1) return "tomorrow";
  if (dayDelta === -1) return "yesterday";
  if (dayDelta > 1 && dayDelta < 7) return `in ${dayDelta} days`;
  if (dayDelta >= 7 && dayDelta < 14) return "next week";
  if (dayDelta >= 14) return `in ${Math.round(dayDelta / 7)} weeks`;
  if (dayDelta < -1 && dayDelta > -7) return `${Math.abs(dayDelta)} days ago`;
  return `${Math.round(Math.abs(dayDelta) / 7)} weeks ago`;
}

/** Compact "saved 4h ago" style stamp. */
export function timeAgo(
  value: string | null | undefined,
  now: Date = new Date(),
): string | null {
  const date = parseDate(value);
  if (!date) return null;
  const seconds = Math.max(0, Math.round((now.getTime() - date.getTime()) / 1000));
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days}d ago`;
  return formatDay(value);
}

export function formatMinutes(minutes: number | null): string | null {
  if (minutes === null || minutes <= 0) return null;
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0 ? `${hours} hr` : `${hours} hr ${rest} min`;
}

export function formatSeconds(seconds: number | null): string | null {
  if (seconds === null || seconds <= 0) return null;
  const mins = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${mins}:${String(rest).padStart(2, "0")}`;
}

export const CONFIDENCE_LABEL: Record<ConfidenceBand, string> = {
  HIGH: "Confident",
  MEDIUM: "Fairly sure",
  LOW: "Guessing",
};

const INTENT_PHRASE: Record<IntentAction, string> = {
  VISIT: "visit it",
  GO: "go there",
  EXPLORE: "explore it",
  ATTEND: "attend it",
  COOK: "cook it",
  TRY: "try it",
  USE: "use it",
  LEARN: "learn it",
  READ: "read it",
  RESEARCH: "look into it",
  OTHER: "come back to it",
};

export function intentPhrase(action: IntentAction): string {
  return INTENT_PHRASE[action];
}

export function pluralise(count: number, word: string): string {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

/** The entity a card should lead with: primary first, else the first one. */
export function primaryEntity(memory: MemoryRead): EntityRead | null {
  return memory.entities.find((entity) => entity.is_primary) ?? memory.entities[0] ?? null;
}

/** The trigger that explains WHEN: a pending one if there is one. */
export function activeTrigger(memory: MemoryRead): TriggerRead | null {
  return (
    memory.triggers.find((trigger) => trigger.status === "PENDING") ??
    memory.triggers[0] ??
    null
  );
}

export interface TriggerCopy {
  /** Human sentence for WHEN. Server-authored `reason` wins when present. */
  headline: string;
  /** Optional supporting stamp: a date, a countdown, a radius. */
  detail: string | null;
}

export function describeTrigger(memory: MemoryRead): TriggerCopy {
  const trigger = activeTrigger(memory);
  if (!trigger) return { headline: "Saved for later", detail: null };

  const parts: string[] = [];
  if (trigger.trigger_type === "DATE" || trigger.trigger_type === "TIME") {
    const stamp = formatDateTime(trigger.fire_at) ?? formatDay(trigger.fire_at);
    const soon = countdown(trigger.fire_at);
    if (stamp) parts.push(stamp);
    if (soon) parts.push(soon);
  }
  if (trigger.trigger_type === "LOCATION" && trigger.radius_meters !== null) {
    parts.push(`within ${trigger.radius_meters} m`);
  }
  if (trigger.status === "FIRED") {
    parts.push(trigger.fire_count > 1 ? `resurfaced ${trigger.fire_count}×` : "resurfaced");
  }

  return {
    headline: trigger.reason.trim() || "Saved for later",
    detail: parts.length > 0 ? parts.join(" · ") : null,
  };
}

/**
 * Ingredient count for RECIPE cards. `EntityRead.details` is free-form on the
 * wire, so this reads it defensively and shows nothing when it is absent.
 */
export function ingredientCount(entity: EntityRead | null): number | null {
  if (!entity) return null;
  const list = entity.details["ingredients"];
  if (Array.isArray(list)) return list.length;
  const count = entity.details["ingredient_count"];
  if (typeof count === "number" && Number.isFinite(count)) return count;
  return null;
}
