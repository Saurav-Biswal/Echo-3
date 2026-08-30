"use client";

import { useAsync } from "@/hooks/useAsync";
import { getMemory, listMemories } from "@/lib/api";
import type { ApiError } from "@/lib/api";
import type { MemoryQuery, MemoryRead, Page } from "@/lib/types";

export interface MemoriesState {
  items: MemoryRead[];
  total: number;
  loading: boolean;
  error: ApiError | null;
  reload: () => void;
}

/** A filtered page of memories. Every filter is a plain query-string param. */
export function useMemories(query: MemoryQuery = {}): MemoriesState {
  const { status, category, limit, offset, q } = query;

  const { data, error, loading, reload } = useAsync<Page<MemoryRead>>(
    (signal) => listMemories({ status, category, limit, offset, q }, signal),
    [status, category, limit, offset, q],
  );

  return {
    items: data?.items ?? [],
    total: data?.total ?? 0,
    loading,
    error,
    reload,
  };
}

export interface MemoryState {
  memory: MemoryRead | null;
  loading: boolean;
  error: ApiError | null;
  reload: () => void;
}

/** One memory by id, for the detail route. */
export function useMemory(id: string): MemoryState {
  const { data, error, loading, reload } = useAsync<MemoryRead>(
    (signal) => getMemory(id, signal),
    [id],
  );
  return { memory: data, loading, error, reload };
}
