package com.example.echo.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Wire models mirroring the Echo backend API (docs/API.md).
 *
 * Enum-like fields (category, status, trigger_type, ...) are modelled as plain
 * [String] on purpose: the backend owns the enum and may add values, and a
 * forgiving client should render an unknown value rather than crash on it.
 * The JSON decoder is configured with ignoreUnknownKeys/coerceInputValues so
 * new backend fields never break an old app.
 */

@Serializable
data class CaptureRequest(
    @SerialName("input_type") val inputType: String,
    val content: String,
    val source: String = "android_share",
    val note: String? = null,
)

@Serializable
data class CaptureResponse(
    @SerialName("job_id") val jobId: String,
    val status: String,
    val duplicate: Boolean = false,
    @SerialName("memory_id") val memoryId: String? = null,
    val message: String? = null,
)

@Serializable
data class JobTimelineEntry(
    val status: String,
    val at: String? = null,
    val detail: String? = null,
)

@Serializable
data class JobDetail(
    val id: String,
    val status: String,
    @SerialName("stage_message") val stageMessage: String? = null,
    val progress: Float = 0f,
    @SerialName("input_type") val inputType: String? = null,
    val origin: String? = null,
    @SerialName("memory_id") val memoryId: String? = null,
    @SerialName("is_duplicate") val isDuplicate: Boolean = false,
    @SerialName("duplicate_of_memory_id") val duplicateOfMemoryId: String? = null,
    @SerialName("error_code") val errorCode: String? = null,
    @SerialName("error_message") val errorMessage: String? = null,
    val attempts: Int = 0,
    val timeline: List<JobTimelineEntry> = emptyList(),
)

@Serializable
data class SourceDto(
    val id: String,
    @SerialName("source_type") val sourceType: String,
    val platform: String,
    @SerialName("media_type") val mediaType: String,
    @SerialName("source_url") val sourceUrl: String? = null,
    val title: String? = null,
    val description: String? = null,
    @SerialName("thumbnail_url") val thumbnailUrl: String? = null,
    val author: String? = null,
    @SerialName("duration_seconds") val durationSeconds: Int? = null,
)

@Serializable
data class EntityDto(
    val id: String,
    @SerialName("entity_type") val entityType: String,
    val name: String,
    val description: String? = null,
    val location: String? = null,
    val address: String? = null,
    val latitude: Double? = null,
    val longitude: Double? = null,
    @SerialName("event_date") val eventDate: String? = null,
    @SerialName("event_time") val eventTime: String? = null,
    val venue: String? = null,
    val url: String? = null,
    val price: String? = null,
    @SerialName("is_primary") val isPrimary: Boolean = false,
)

@Serializable
data class TriggerDto(
    val id: String,
    @SerialName("trigger_type") val triggerType: String,
    val status: String,
    val reason: String,
    @SerialName("fire_at") val fireAt: String? = null,
    val latitude: Double? = null,
    val longitude: Double? = null,
    @SerialName("radius_meters") val radiusMeters: Int? = null,
    @SerialName("place_label") val placeLabel: String? = null,
)

@Serializable
data class ActionDto(
    val id: String,
    @SerialName("action_type") val actionType: String,
    val label: String,
    @SerialName("deep_link") val deepLink: String? = null,
    @SerialName("web_link") val webLink: String? = null,
    @SerialName("is_primary") val isPrimary: Boolean = false,
    @SerialName("sort_order") val sortOrder: Int = 0,
)

/**
 * A resurfacing notification the backend has sent (§22). The device polls these
 * (status=SENT) and raises a system notification for each new one. [actions] is
 * the snapshot the backend took at send time.
 */
@Serializable
data class NotificationDto(
    val id: String,
    @SerialName("memory_id") val memoryId: String,
    val category: String,
    @SerialName("trigger_type") val triggerType: String,
    val title: String,
    val body: String,
    val why: String,
    val status: String,
    @SerialName("sent_at") val sentAt: String? = null,
    val actions: List<ActionDto> = emptyList(),
)

/** Page envelope the backend wraps list responses in: {items,total,limit,offset}. */
@Serializable
data class NotificationPage(
    val items: List<NotificationDto> = emptyList(),
    val total: Int = 0,
    val limit: Int = 0,
    val offset: Int = 0,
)

/** Generic acknowledgement body ({"message": "..."}). */
@Serializable
data class Ack(
    val message: String? = null,
)
