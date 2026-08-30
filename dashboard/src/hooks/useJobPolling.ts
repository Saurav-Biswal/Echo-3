"use client";

import { useEffect, useRef, useState } from "react";

import { getJob, getMemory, toApiError } from "@/lib/api";
import type { ApiError } from "@/lib/api";
import type { JobDetailRead, MemoryRead } from "@/lib/types";

const POLL_INTERVAL_MS = 1_200;

export interface JobPollingState {
  job: JobDetailRead | null;
  /** Filled once the job completes and the memory has been fetched. */
  memory: MemoryRead | null;
  error: ApiError | null;
  /** True once the job reached COMPLETED or FAILED. */
  settled: boolean;
}

function isTerminal(job: JobDetailRead): boolean {
  return job.status === "COMPLETED" || job.status === "FAILED";
}

/**
 * Polls `GET /api/jobs/{id}` every ~1.2 s until the job settles, then loads the
 * memory it produced. Passing `null` keeps the hook idle.
 */
export function useJobPolling(jobId: string | null): JobPollingState {
  const [job, setJob] = useState<JobDetailRead | null>(null);
  const [memory, setMemory] = useState<MemoryRead | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [settled, setSettled] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setJob(null);
    setMemory(null);
    setError(null);
    setSettled(false);
    if (!jobId) return;

    const controller = new AbortController();
    let alive = true;

    const stop = () => {
      alive = false;
      if (timer.current !== null) clearTimeout(timer.current);
      timer.current = null;
      controller.abort();
    };

    const tick = async (): Promise<void> => {
      try {
        const next = await getJob(jobId, controller.signal);
        if (!alive) return;
        setJob(next);

        if (!isTerminal(next)) {
          timer.current = setTimeout(() => void tick(), POLL_INTERVAL_MS);
          return;
        }

        setSettled(true);
        const memoryId = next.memory_id ?? next.duplicate_of_memory_id;
        if (next.status === "COMPLETED" && memoryId) {
          const saved = await getMemory(memoryId, controller.signal);
          if (alive) setMemory(saved);
        }
      } catch (cause: unknown) {
        if (!alive || controller.signal.aborted) return;
        setError(toApiError(cause));
        setSettled(true);
      }
    };

    void tick();
    return stop;
  }, [jobId]);

  return { job, memory, error, settled };
}
