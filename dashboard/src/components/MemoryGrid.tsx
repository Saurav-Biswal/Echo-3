import { MemoryCard } from "@/components/MemoryCard";
import type { MemoryRead } from "@/lib/types";
import { cn } from "@/lib/ui";

/** The one responsive grid all card lists use: 1 → 2 → 3 columns. */
export function MemoryGrid({
  memories,
  showResolver = false,
  className,
}: {
  memories: MemoryRead[];
  showResolver?: boolean;
  className?: string;
}) {
  return (
    <div className={cn("grid gap-4 sm:grid-cols-2 xl:grid-cols-3", className)}>
      {memories.map((memory) => (
        <MemoryCard key={memory.id} memory={memory} showResolver={showResolver} />
      ))}
    </div>
  );
}
