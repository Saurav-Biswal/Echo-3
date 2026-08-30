/**
 * The only module in the dashboard that is allowed to call `fetch`.
 *
 * Everything goes through `request()`, which:
 *  - joins the path onto NEXT_PUBLIC_ECHO_API_URL,
 *  - aborts after a timeout instead of hanging the UI,
 *  - turns `{"error": {code, message, hint}}` into a typed `ApiError`,
 *  - turns an unreachable backend into a recognisable `NETWORK` ApiError,
 *  - never lets raw response text reach a component.
 */

import type {
  CaptureRequest,
  CaptureResponse,
  ErrorResponse,
  HealthResponse,
  JobDetailRead,
  MemoryCorrection,
  MemoryQuery,
  MemoryRead,
  MemoryUpdate,
  NotificationAck,
  NotificationRead,
  NotificationStatus,
  OverviewResponse,
  Page,
  ProcessRequest,
  ResurfaceRequest,
  ResurfaceResponse,
  SeedResponse,
  SimulateDateRequest,
  SimulateLocationRequest,
} from "@/lib/types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_ECHO_API_URL ?? "http://localhost:8000";

const DEFAULT_TIMEOUT_MS = 12_000;

/** Codes this client produces itself, i.e. never sent by the backend. */
export const CLIENT_ERROR_CODES = {
  network: "ECHO_UNREACHABLE",
  timeout: "ECHO_TIMEOUT",
  malformed: "ECHO_BAD_RESPONSE",
} as const;

export class ApiError extends Error {
  readonly code: string;
  readonly status: number | null;
  readonly hint: string | null;

  constructor(opts: {
    code: string;
    message: string;
    status?: number | null;
    hint?: string | null;
  }) {
    super(opts.message);
    this.name = "ApiError";
    this.code = opts.code;
    this.status = opts.status ?? null;
    this.hint = opts.hint ?? null;
  }

  /** True when Echo's backend could not be reached at all. */
  get isOffline(): boolean {
    return (
      this.code === CLIENT_ERROR_CODES.network ||
      this.code === CLIENT_ERROR_CODES.timeout
    );
  }
}

/** Normalises anything thrown inside a hook into an ApiError. */
export function toApiError(cause: unknown): ApiError {
  if (cause instanceof ApiError) return cause;
  return new ApiError({
    code: CLIENT_ERROR_CODES.malformed,
    message: "Something went wrong while talking to Echo.",
  });
}

function isErrorResponse(value: unknown): value is ErrorResponse {
  if (typeof value !== "object" || value === null) return false;
  const body = (value as { error?: unknown }).error;
  if (typeof body !== "object" || body === null) return false;
  const { code, message } = body as { code?: unknown; message?: unknown };
  return typeof code === "string" && typeof message === "string";
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number | undefined>;
  signal?: AbortSignal;
  timeoutMs?: number;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const base = API_BASE_URL.replace(/\/+$/, "");
  const url = new URL(`${base}${path}`);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== "") url.searchParams.set(key, String(value));
  }
  return url.toString();
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, query, signal, timeoutMs = DEFAULT_TIMEOUT_MS } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const onOuterAbort = () => controller.abort();
  signal?.addEventListener("abort", onOuterAbort);

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      cache: "no-store",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
  } catch {
    // Distinguish "the caller cancelled" from "nothing is listening".
    if (signal?.aborted) {
      throw new ApiError({
        code: CLIENT_ERROR_CODES.timeout,
        message: "Request cancelled.",
      });
    }
    throw new ApiError({
      code: controller.signal.aborted
        ? CLIENT_ERROR_CODES.timeout
        : CLIENT_ERROR_CODES.network,
      message: controller.signal.aborted
        ? "Echo's backend took too long to answer."
        : "Can't reach Echo's backend.",
      hint: `Expected it at ${API_BASE_URL}. Start the API, then retry.`,
    });
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onOuterAbort);
  }

  if (response.status === 204) return undefined as T;

  const raw = await response.text();
  let parsed: unknown = null;
  if (raw.length > 0) {
    try {
      parsed = JSON.parse(raw) as unknown;
    } catch {
      parsed = null;
    }
  }

  if (!response.ok) {
    if (isErrorResponse(parsed)) {
      throw new ApiError({
        code: parsed.error.code,
        message: parsed.error.message,
        hint: parsed.error.hint ?? null,
        status: response.status,
      });
    }
    throw new ApiError({
      code: `HTTP_${response.status}`,
      message: `Echo replied with ${response.status} ${response.statusText || "error"}.`,
      status: response.status,
    });
  }

  if (parsed === null) {
    throw new ApiError({
      code: CLIENT_ERROR_CODES.malformed,
      message: "Echo returned an unreadable response.",
      status: response.status,
    });
  }
  return parsed as T;
}

/* -------------------------------------------------------------------------- */
/* Endpoints                                                                  */
/* -------------------------------------------------------------------------- */

export const getHealth = (signal?: AbortSignal) =>
  request<HealthResponse>("/api/health", { signal, timeoutMs: 4_000 });

export const getOverview = (signal?: AbortSignal) =>
  request<OverviewResponse>("/api/overview", { signal });

export const listMemories = (query: MemoryQuery = {}, signal?: AbortSignal) =>
  request<Page<MemoryRead>>("/api/memories", {
    query: {
      status: query.status,
      category: query.category,
      limit: query.limit,
      offset: query.offset,
      q: query.q,
    },
    signal,
  });

export const getMemory = (id: string, signal?: AbortSignal) =>
  request<MemoryRead>(`/api/memories/${encodeURIComponent(id)}`, { signal });

export const updateMemory = (id: string, patch: MemoryUpdate) =>
  request<MemoryRead>(`/api/memories/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: patch,
  });

export const deleteMemory = (id: string) =>
  request<void>(`/api/memories/${encodeURIComponent(id)}`, { method: "DELETE" });

export const correctMemory = (id: string, correction: MemoryCorrection) =>
  request<MemoryRead>(`/api/memories/${encodeURIComponent(id)}/correct`, {
    method: "POST",
    body: correction,
  });

export const captureMemory = (payload: CaptureRequest) =>
  request<CaptureResponse>("/api/capture", { method: "POST", body: payload });

export const getJob = (jobId: string, signal?: AbortSignal) =>
  request<JobDetailRead>(`/api/jobs/${encodeURIComponent(jobId)}`, {
    signal,
    timeoutMs: 6_000,
  });

export const reprocess = (payload: ProcessRequest) =>
  request<CaptureResponse>("/api/process", { method: "POST", body: payload });

export const listNotifications = (
  query: { status?: NotificationStatus; limit?: number; offset?: number } = {},
  signal?: AbortSignal,
) =>
  request<Page<NotificationRead>>("/api/notifications", {
    query: { status: query.status, limit: query.limit, offset: query.offset },
    signal,
  });

export const ackNotification = (id: string, action: NotificationAck) =>
  request<NotificationRead>(`/api/notifications/${encodeURIComponent(id)}/ack`, {
    method: "POST",
    body: { action },
  });

export const forceResurface = (payload: ResurfaceRequest) =>
  request<ResurfaceResponse>("/api/test/resurface", { method: "POST", body: payload });

export const simulateLocation = (payload: SimulateLocationRequest) =>
  request<ResurfaceResponse>("/api/demo/simulate-location", {
    method: "POST",
    body: payload,
  });

export const simulateDate = (payload: SimulateDateRequest) =>
  request<ResurfaceResponse>("/api/demo/simulate-date", {
    method: "POST",
    body: payload,
  });

export const seedDemoData = () =>
  request<SeedResponse>("/api/demo/seed", { method: "POST", timeoutMs: 30_000 });
