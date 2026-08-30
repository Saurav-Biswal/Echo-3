import { cn, surface } from "@/lib/ui";

/** A single shimmering placeholder bar. */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn("echo-pulse rounded bg-ink-700", className)}
    />
  );
}

/** Placeholder in the exact shape of a MemoryCard, so nothing jumps on load. */
export function SkeletonCard() {
  return (
    <div className={cn(surface, "relative overflow-hidden p-5")}>
      <div className="absolute inset-y-4 left-0 w-[2px] rounded-full bg-ink-700" />
      <div className="space-y-3 pl-3">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-5 w-4/5" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-9 w-32 rounded-lg" />
      </div>
    </div>
  );
}

export function SkeletonGrid({ count = 4 }: { count?: number }) {
  return (
    <div
      className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
      role="status"
      aria-label="Loading memories"
    >
      {Array.from({ length: count }, (_, index) => (
        <SkeletonCard key={index} />
      ))}
    </div>
  );
}

export function SkeletonTiles({ count = 4 }: { count?: number }) {
  return (
    <div
      className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
      role="status"
      aria-label="Loading counts"
    >
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className={cn(surface, "space-y-3 p-5")}>
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-8 w-12" />
        </div>
      ))}
    </div>
  );
}
