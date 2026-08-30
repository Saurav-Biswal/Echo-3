import {
  countdown,
  formatDay,
  formatMinutes,
  ingredientCount,
  primaryEntity,
} from "@/lib/format";
import type { MemoryRead } from "@/lib/types";
import { cn } from "@/lib/ui";

interface Fact {
  label: string;
  value: string;
}

function Facts({ facts, className }: { facts: Fact[]; className?: string }) {
  if (facts.length === 0) return null;
  return (
    <dl className={cn("flex flex-wrap gap-x-5 gap-y-2", className)}>
      {facts.map((fact) => (
        <div key={fact.label} className="min-w-0">
          <dt className="font-mono text-[10px] uppercase tracking-[0.16em] text-fog-500">
            {fact.label}
          </dt>
          <dd className="truncate text-[13px] text-fog-200">{fact.value}</dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * The category-appropriate detail line: a PLACE needs a city, an EVENT needs a
 * countdown, a RECIPE needs its shape. Anything missing is simply not shown.
 */
export function CategoryDetail({
  memory,
  className,
}: {
  memory: MemoryRead;
  className?: string;
}) {
  const entity = primaryEntity(memory);
  const facts: Fact[] = [];

  if (memory.category === "PLACE") {
    const where = entity?.location ?? entity?.address;
    if (where) facts.push({ label: "City", value: where });
    if (entity?.price) facts.push({ label: "Typical", value: entity.price });
    facts.push({ label: "Resurfaces", value: "When you're nearby" });
  }

  if (memory.category === "EVENT") {
    const when = entity?.starts_at ?? entity?.event_date;
    const day = formatDay(when);
    if (day) facts.push({ label: "Date", value: day });
    if (entity?.event_time) facts.push({ label: "Time", value: entity.event_time });
    if (entity?.venue) facts.push({ label: "Venue", value: entity.venue });
    const soon = countdown(when);
    if (soon) facts.push({ label: "Countdown", value: soon });
  }

  if (memory.category === "RECIPE") {
    const count = ingredientCount(entity);
    if (count !== null) {
      facts.push({ label: "Ingredients", value: String(count) });
    }
    const cooking = formatMinutes(entity?.duration_minutes ?? null);
    if (cooking) facts.push({ label: "Cooking time", value: cooking });
  }

  if (memory.category === "TOOL") {
    const purpose = entity?.description ?? memory.summary;
    if (purpose) facts.push({ label: "What it's for", value: purpose });
  }

  if (memory.category === "TOPIC") {
    const idea = entity?.description ?? memory.summary;
    if (idea) facts.push({ label: "Key idea", value: idea });
  }

  return <Facts facts={facts} className={className} />;
}
