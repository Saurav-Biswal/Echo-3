"use client";

import { EmptyState, ErrorState } from "@/components/EmptyState";
import { MemoryGrid } from "@/components/MemoryGrid";
import { PageHeader } from "@/components/PageHeader";
import { SkeletonGrid } from "@/components/Skeleton";
import { useMemories } from "@/hooks/useMemories";
import type { MemoryQuery } from "@/lib/types";
import { eyebrow } from "@/lib/ui";

export interface MemoryListViewProps {
  label: string;
  title: string;
  lede: string;
  query: MemoryQuery;
  empty: { title: string; body: string; glyph?: string };
  /** Needs-review lists offer the five category buttons on every card. */
  showResolver?: boolean;
}

/**
 * Every filtered list in the dashboard — the five categories, Resurfaced,
 * Completed, Needs review — is this one view with a different query.
 */
export function MemoryListView({
  label,
  title,
  lede,
  query,
  empty,
  showResolver = false,
}: MemoryListViewProps) {
  const { items, total, loading, error, reload } = useMemories({ limit: 60, ...query });

  return (
    <div className="space-y-7">
      <PageHeader
        label={label}
        title={title}
        lede={lede}
        aside={
          !loading && !error ? (
            <p className={eyebrow}>{total === 1 ? "1 memory" : `${total} memories`}</p>
          ) : null
        }
      />

      {loading ? <SkeletonGrid /> : null}
      {!loading && error ? <ErrorState error={error} onRetry={reload} /> : null}
      {!loading && !error && items.length === 0 ? (
        <EmptyState
          title={empty.title}
          body={empty.body}
          glyph={empty.glyph}
          action={{ label: "Save something", href: "/capture" }}
        />
      ) : null}
      {!loading && !error && items.length > 0 ? (
        <MemoryGrid memories={items} showResolver={showResolver} />
      ) : null}
    </div>
  );
}
