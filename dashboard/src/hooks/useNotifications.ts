"use client";

import { useCallback, useMemo, useState } from "react";

import { useAsync } from "@/hooks/useAsync";
import { ackNotification, listNotifications } from "@/lib/api";
import type { ApiError } from "@/lib/api";
import type { NotificationAck, NotificationRead, Page } from "@/lib/types";

export interface NotificationsState {
  items: NotificationRead[];
  loading: boolean;
  error: ApiError | null;
  reload: () => void;
  /** Merge notifications a demo control just returned, newest first. */
  push: (incoming: NotificationRead[]) => void;
  ack: (id: string, action: NotificationAck) => Promise<void>;
}

function newestFirst(items: NotificationRead[]): NotificationRead[] {
  const seen = new Set<string>();
  return items
    .filter((item) => {
      if (seen.has(item.id)) return false;
      seen.add(item.id);
      return true;
    })
    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
}

/**
 * The resurfacing feed. Server state plus anything the demo panel just fired,
 * so a simulated notification appears instantly instead of after a refetch.
 */
export function useNotifications(limit = 20): NotificationsState {
  const { data, error, loading, reload } = useAsync<Page<NotificationRead>>(
    (signal) => listNotifications({ limit }, signal),
    [limit],
  );
  const [local, setLocal] = useState<NotificationRead[]>([]);

  const items = useMemo(
    () => newestFirst([...local, ...(data?.items ?? [])]),
    [local, data],
  );

  const push = useCallback((incoming: NotificationRead[]) => {
    if (incoming.length === 0) return;
    setLocal((prev) => newestFirst([...incoming, ...prev]));
  }, []);

  const ack = useCallback(
    async (id: string, action: NotificationAck) => {
      const updated = await ackNotification(id, action);
      setLocal((prev) => prev.map((item) => (item.id === id ? updated : item)));
      reload();
    },
    [reload],
  );

  return { items, loading, error, reload, push, ack };
}
