"use client";

import Link from "next/link";

import type { ApiError } from "@/lib/api";
import { API_BASE_URL } from "@/lib/api";
import { btnSecondary, cn, surface } from "@/lib/ui";

/** A real empty state, with copy in Echo's voice — never a blank panel. */
export function EmptyState({
  title,
  body,
  glyph = "◌",
  action,
}: {
  title: string;
  body: string;
  glyph?: string;
  action?: { label: string; href: string };
}) {
  return (
    <div
      className={cn(
        surface,
        "flex flex-col items-center gap-3 border-dashed px-6 py-14 text-center",
      )}
    >
      <span aria-hidden="true" className="text-2xl text-fog-600">
        {glyph}
      </span>
      <h2 className="text-base font-medium text-fog-100">{title}</h2>
      <p className="max-w-sm text-sm leading-relaxed text-fog-400">{body}</p>
      {action ? (
        <Link href={action.href} className={cn(btnSecondary, "mt-2")}>
          {action.label}
        </Link>
      ) : null}
    </div>
  );
}

/**
 * The failure state every data view falls back to. An unreachable backend gets
 * its own copy, because during a demo that is the likely cause.
 */
export function ErrorState({
  error,
  onRetry,
}: {
  error: ApiError;
  onRetry?: () => void;
}) {
  const offline = error.isOffline;

  return (
    <div
      role="alert"
      className={cn(surface, "space-y-3 border-[#4a2530] bg-[#170f12]/70 p-6")}
    >
      <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#ff9aa5]">
        {offline ? "Backend unreachable" : error.code}
      </p>
      <h2 className="text-base font-medium text-fog-50">
        {offline ? "Can't reach Echo's backend." : error.message}
      </h2>
      <p className="text-sm leading-relaxed text-fog-400">
        {offline
          ? `Nothing is answering at ${API_BASE_URL}. Start the API, then retry — the dashboard keeps working either way.`
          : (error.hint ?? "Echo refused that request. Nothing was changed.")}
      </p>
      {onRetry ? (
        <button type="button" onClick={onRetry} className={btnSecondary}>
          Retry
        </button>
      ) : null}
    </div>
  );
}
