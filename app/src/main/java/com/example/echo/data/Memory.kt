package com.example.echo.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** Memory card payload - shaped so What / Why / When / Action all travel together (§26). */
@Serializable
data class MemoryDto(
    val id: String,
    // --- what ---
    val category: String,
    val title: String,
    val summary: String? = null,
    // --- why (the product) ---
    @SerialName("why_saved") val whySaved: String,
    @SerialName("intent_action") val intentAction: String,
    @SerialName("intent_confidence") val intentConfidence: Float = 0f,
    @SerialName("confidence_band") val confidenceBand: String,
    // --- lifecycle ---
    val status: String,
    @SerialName("needs_review_reason") val needsReviewReason: String? = null,
    @SerialName("resurface_count") val resurfaceCount: Int = 0,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
    @SerialName("user_confirmed") val userConfirmed: Boolean = false,
    @SerialName("user_corrected") val userCorrected: Boolean = false,
    val source: SourceDto? = null,
    val entities: List<EntityDto> = emptyList(),
    val triggers: List<TriggerDto> = emptyList(),
    val actions: List<ActionDto> = emptyList(),
)

@Serializable
data class CategoryCount(
    val category: String,
    val count: Int,
)

@Serializable
data class OverviewResponse(
    val active: Int = 0,
    val resurfaced: Int = 0,
    val completed: Int = 0,
    @SerialName("needs_review") val needsReview: Int = 0,
    @SerialName("by_category") val byCategory: List<CategoryCount> = emptyList(),
    @SerialName("upcoming_trigger_at") val upcomingTriggerAt: String? = null,
    val recent: List<MemoryDto> = emptyList(),
)

@Serializable
data class MemoryCorrection(
    val category: String? = null,
    @SerialName("intent_action") val intentAction: String? = null,
    val note: String? = null,
    val confirmed: Boolean = false,
)

/** Single error envelope every failure returns (§41): {"error":{code,message,hint?}}. */
@Serializable
data class ErrorBody(
    val code: String,
    val message: String,
    val hint: String? = null,
)

@Serializable
data class ErrorResponse(
    val error: ErrorBody,
)
