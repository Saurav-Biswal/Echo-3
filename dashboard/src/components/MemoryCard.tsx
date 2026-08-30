"use client";

import Link from "next/link";
import { useState } from "react";

import { ActionButtons } from "@/components/ActionButtons";
import { CategoryBadge } from "@/components/CategoryBadge";
import { CategoryDetail } from "@/components/CategoryDetail";
import { ConfidenceMeter } from "@/components/ConfidenceMeter";
import { CategoryResolver } from "@/components/CorrectionControls";
import { StatusPill } from "@/components/StatusPill";
import { TriggerLine } from "@/components/TriggerLine";
import { WhySavedBlock } from "@/components/WhySavedBlock";
import { timeAgo } from "@/lib/format";
import type { MemoryRead } from "@/lib/types";
import { cn, surface } from "@/lib/ui";

/**
 * The unit of the whole dashboard. It answers, in this order:
 * WHAT (title) → WHY (why_saved) → WHEN (trigger) → ACTION (primary button).
 * `summary` is supporting detail and is deliberately last and quiet.
 */
export function MemoryCard({
  memory: initial,
  showResolver = false,
}: {
  memory: MemoryRead;
  showResolver?: boolean;
}) {
  const [memory, setMemory] = useState(initial);
  const saved = timeAgo(memory.created_at);

  return (
    <article
      data-category={memory.category}
      className={cn(
        surface,
        "relative flex flex-col gap-3.5 overflow-hidden p-5 pl-6",
        "transition-colors hover:border-[color:color-mix(in_srgb,var(--cat)_40%,var(--color-line))]",
      )}
    >
      {/* the per-card accent rail */}
      <span
        aria-hidden="true"
        className="absolute inset-y-0 left-0 w-[2px] bg-[var(--cat)] opacity-70"
      />

      <header className="flex flex-wrap items-center gap-2">
        <CategoryBadge category={memory.category} />
        <StatusPill status={memory.status} />
        {saved ? (
          <span className="ml-auto font-mono text-[10px] uppercase tracking-[0.14em] text-fog-600">
            saved {saved}
          </span>
        ) : null}
      </header>

      {/* WHAT */}
      <h3 className="text-[17px] leading-snug font-semibold text-fog-50">
        <Link
          href={`/memories/${memory.id}`}
          className="rounded transition-colors hover:text-[color:var(--cat)]"
        >
          {memory.title}
        </Link>
      </h3>

      {/* WHY */}
      <WhySavedBlock whySaved={memory.why_saved} />

      {/* WHEN */}
      <TriggerLine memory={memory} />

      <CategoryDetail memory={memory} />

      {memory.summary ? (
        <p className="line-clamp-2 text-[13px] leading-relaxed text-fog-500">
          {memory.summary}
        </p>
      ) : null}

      {/* ACTION */}
      <footer className="mt-auto flex flex-wrap items-center justify-between gap-3 pt-1">
        <ActionButtons actions={memory.actions} />
        <ConfidenceMeter
          band={memory.confidence_band}
          score={memory.intent_confidence}
          showLabel={false}
        />
      </footer>

      {showResolver ? (
        <CategoryResolver memory={memory} onUpdated={setMemory} />
      ) : null}
    </article>
  );
}
