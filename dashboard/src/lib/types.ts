/**
 * Wire types for the Echo API, mirroring docs/API.md exactly.
 *
 * Field names, enum members and nullability come straight from the contract.
 * Nothing here is invented: anything free-form on the wire (`details`,
 * `action_metadata`, `payload`) is typed as `JsonObject`, not `any`.
 */

export type JsonObject = Record<string, unknown>;

/* -------------------------------------------------------------------------- */
/* Enums                                                                      */
/* -------------------------------------------------------------------------- */

export type Category = "PLACE" | "EVENT" | "RECIPE" | "TOOL" | "TOPIC";

export type IntentAction =
  | "VISIT"
  | "GO"
  | "EXPLORE"
  | "ATTEND"
  | "COOK"
  | "TRY"
  | "USE"
  | "LEARN"
  | "READ"
  | "RESEARCH"
  | "OTHER";

export type MemoryStatus =
  | "ACTIVE"
  | "RESURFACED"
  | "COMPLETED"
  | "DISMISSED"
  | "ARCHIVED"
  | "NEEDS_REVIEW";

export type ConfidenceBand = "HIGH" | "MEDIUM" | "LOW";

export type TriggerType = "DATE" | "TIME" | "LOCATION" | "MANUAL";

export type TriggerStatus = "PENDING" | "FIRED" | "CANCELLED";

export type ActionType =
  | "OPEN_MAPS"
  | "ADD_TO_CALENDAR"
  | "OPEN_EVENT"
  | "VIEW_RECIPE"
  | "OPEN_TOOL"
  | "OPEN_SOURCE"
  | "OPEN_URL"
  | "SET_REMINDER";

export type JobStatus =
  | "QUEUED"
  | "FETCHING"
  | "ANALYZING"
  | "EXTRACTING_INTENT"
  | "VALIDATING"
  | "SAVING"
  | "COMPLETED"
  | "FAILED";

export type SourceType =
  | "youtube_short"
  | "youtube_video"
  | "instagram_reel"
  | "instagram_post"
  | "web_url"
  | "screenshot"
  | "text";

export type Platform = "youtube" | "instagram" | "web" | "device";

export type MediaType = "video" | "image" | "text" | "none";

export type InputType = "url" | "text" | "image";

export type NotificationStatus = "SCHEDULED" | "SENT" | "ACTED" | "DISMISSED";

export type EntityType = "PLACE" | "EVENT" | "RECIPE" | "TOOL" | "TOPIC";

/* -------------------------------------------------------------------------- */
/* Envelopes                                                                  */
/* -------------------------------------------------------------------------- */

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ErrorBody {
  code: string;
  message: string;
  hint?: string | null;
}

export interface ErrorResponse {
  error: ErrorBody;
}

export interface HealthResponse {
  status: string;
  app: string;
  env: string;
  ai_provider: string;
  database: string;
  demo_mode: boolean;
}

/* -------------------------------------------------------------------------- */
/* Capture + jobs                                                             */
/* -------------------------------------------------------------------------- */

export interface CaptureRequest {
  input_type: InputType;
  content: string;
  source: string;
  note: string | null;
}

export interface CaptureResponse {
  job_id: string;
  status: JobStatus;
  duplicate: boolean;
  memory_id: string | null;
  message: string | null;
}

export interface ProcessRequest {
  memory_id?: string;
  job_id?: string;
}

export interface JobTimelineEntry {
  status: JobStatus;
  at: string;
  detail: string | null;
}

export interface JobDetailRead {
  id: string;
  status: JobStatus;
  stage_message: string | null;
  progress: number;
  input_type: InputType;
  origin: string;
  source_type: SourceType | null;
  platform: Platform | null;
  memory_id: string | null;
  is_duplicate: boolean;
  duplicate_of_memory_id: string | null;
  error_code: string | null;
  error_message: string | null;
  attempts: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  timeline: JobTimelineEntry[];
}

/* -------------------------------------------------------------------------- */
/* Memory                                                                     */
/* -------------------------------------------------------------------------- */

export interface SourceRead {
  id: string;
  source_type: SourceType;
  platform: Platform;
  media_type: MediaType;
  source_url: string | null;
  title: string | null;
  description: string | null;
  thumbnail_url: string | null;
  author: string | null;
  duration_seconds: number | null;
}

export interface EntityRead {
  id: string;
  entity_type: EntityType;
  name: string;
  description: string | null;
  location: string | null;
  address: string | null;
  latitude: number | null;
  longitude: number | null;
  event_date: string | null;
  event_time: string | null;
  starts_at: string | null;
  ends_at: string | null;
  venue: string | null;
  url: string | null;
  price: string | null;
  duration_minutes: number | null;
  details: JsonObject;
  confidence: number;
  is_primary: boolean;
}

export interface TriggerRead {
  id: string;
  memory_id: string;
  trigger_type: TriggerType;
  status: TriggerStatus;
  reason: string;
  fire_at: string | null;
  latitude: number | null;
  longitude: number | null;
  radius_meters: number | null;
  place_label: string | null;
  fired_at: string | null;
  fire_count: number;
  created_at: string;
}

export interface ActionRead {
  id: string;
  action_type: ActionType;
  label: string;
  deep_link: string | null;
  web_link: string | null;
  action_metadata: JsonObject;
  is_primary: boolean;
  sort_order: number;
}

export interface MemoryRead {
  id: string;
  category: Category;
  title: string;
  summary: string | null;
  why_saved: string;
  intent_action: IntentAction;
  intent_confidence: number;
  confidence_band: ConfidenceBand;
  status: MemoryStatus;
  needs_review_reason: string | null;
  resurface_count: number;
  resurfaced_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  user_confirmed: boolean;
  user_corrected: boolean;
  ai_model: string | null;
  source: SourceRead | null;
  entities: EntityRead[];
  triggers: TriggerRead[];
  actions: ActionRead[];
}

export interface MemoryUpdate {
  status?: MemoryStatus;
  title?: string;
  why_saved?: string;
}

export interface MemoryCorrection {
  category?: Category;
  intent_action?: IntentAction;
  note?: string;
  confirmed?: boolean;
}

export interface MemoryQuery {
  status?: MemoryStatus;
  category?: Category;
  limit?: number;
  offset?: number;
  q?: string;
}

/* -------------------------------------------------------------------------- */
/* Overview                                                                   */
/* -------------------------------------------------------------------------- */

export interface CategoryCount {
  category: Category;
  count: number;
}

export interface OverviewResponse {
  active: number;
  resurfaced: number;
  completed: number;
  needs_review: number;
  by_category: CategoryCount[];
  upcoming_trigger_at: string | null;
  recent: MemoryRead[];
}

/* -------------------------------------------------------------------------- */
/* Notifications + demo controls                                              */
/* -------------------------------------------------------------------------- */

export interface NotificationRead {
  id: string;
  memory_id: string;
  category: Category;
  trigger_type: TriggerType;
  title: string;
  body: string;
  why: string;
  status: NotificationStatus;
  scheduled_at: string | null;
  sent_at: string | null;
  created_at: string;
  actions: ActionRead[];
  payload: JsonObject;
}

export type NotificationAck = "SENT" | "ACTED" | "DISMISSED";

export interface SimulateLocationRequest {
  memory_id?: string;
  latitude?: number;
  longitude?: number;
}

export interface SimulateDateRequest {
  memory_id?: string;
  as_of?: string;
}

export interface ResurfaceRequest {
  memory_id: string;
  trigger_type?: TriggerType | null;
}

export interface ResurfaceResponse {
  fired: number;
  notifications: NotificationRead[];
  message: string | null;
}

export interface SeedResponse {
  created: number;
}
