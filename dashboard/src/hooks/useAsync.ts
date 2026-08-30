"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { type ApiError, toApiError } from "@/lib/api";

export interface AsyncState<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  reload: () => void;
}

/**
 * The one data-loading primitive the dashboard uses: run `loader` whenever
 * `deps` change, cancel the in-flight request on unmount, and surface failures
 * as a typed ApiError instead of throwing into render.
 */
export function useAsync<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  deps: readonly unknown[],
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);

  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  useEffect(() => {
    const controller = new AbortController();
    let alive = true;
    setLoading(true);
    setError(null);

    loaderRef.current(controller.signal).then(
      (result) => {
        if (!alive) return;
        setData(result);
        setLoading(false);
      },
      (cause: unknown) => {
        if (!alive || controller.signal.aborted) return;
        setError(toApiError(cause));
        setData(null);
        setLoading(false);
      },
    );

    return () => {
      alive = false;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nonce, ...deps]);

  const reload = useCallback(() => setNonce((value) => value + 1), []);

  return { data, error, loading, reload };
}
