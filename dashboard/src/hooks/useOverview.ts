"use client";

import { useAsync } from "@/hooks/useAsync";
import { getOverview } from "@/lib/api";
import type { ApiError } from "@/lib/api";
import type { OverviewResponse } from "@/lib/types";

export interface OverviewState {
  overview: OverviewResponse | null;
  loading: boolean;
  error: ApiError | null;
  reload: () => void;
}

/** The dashboard header numbers, in one request. */
export function useOverview(): OverviewState {
  const { data, error, loading, reload } = useAsync<OverviewResponse>(
    (signal) => getOverview(signal),
    [],
  );
  return { overview: data, loading, error, reload };
}
