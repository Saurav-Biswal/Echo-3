package com.example.echo.ui

import com.example.echo.data.ActionDto
import com.example.echo.data.MemoryDto
import com.example.echo.data.TriggerDto

/** Presentation helpers that turn raw wire strings into human-facing copy. */
object Display {

    fun categoryEmoji(category: String): String = when (category.uppercase()) {
        "PLACE" -> "📍"
        "EVENT" -> "📅"
        "RECIPE" -> "🍳"
        "TOOL" -> "🛠️"
        "TOPIC" -> "📖"
        else -> "✨"
    }

    fun categoryLabel(category: String): String = when (category.uppercase()) {
        "PLACE" -> "Place"
        "EVENT" -> "Event"
        "RECIPE" -> "Recipe"
        "TOOL" -> "Tool"
        "TOPIC" -> "Topic"
        else -> category.lowercase().replaceFirstChar { it.uppercase() }
    }

    /**
     * The "When" line (§26). triggers[] may be empty - the API contract says to
     * fall back to "Saved for later" rather than showing nothing.
     */
    fun whenLine(triggers: List<TriggerDto>): String {
        val active = triggers.firstOrNull { it.status.equals("PENDING", ignoreCase = true) }
            ?: triggers.firstOrNull()
            ?: return "Saved for later"
        return active.reason.ifBlank {
            when (active.triggerType.uppercase()) {
                "LOCATION" -> active.placeLabel?.let { "When you're near $it" } ?: "When you're nearby"
                "DATE", "TIME" -> active.fireAt?.let { "On ${prettyDate(it)}" } ?: "At the right time"
                "MANUAL" -> "When you ask"
                else -> "Saved for later"
            }
        }
    }

    /** entities[] may be empty - fall back to the title (API renderer note). */
    fun cardTitle(memory: MemoryDto): String =
        memory.entities.firstOrNull { it.isPrimary }?.name
            ?: memory.entities.firstOrNull()?.name
            ?: memory.title

    /** Actions in display order, primary first, then sort_order. */
    fun orderedActions(actions: List<ActionDto>): List<ActionDto> =
        actions.sortedWith(compareByDescending<ActionDto> { it.isPrimary }.thenBy { it.sortOrder })

    /** A usable link for an action, preferring the Android deep link. */
    fun actionLink(action: ActionDto): String? =
        action.deepLink?.takeIf { it.isNotBlank() } ?: action.webLink?.takeIf { it.isNotBlank() }

    fun confidenceLabel(band: String): String = when (band.uppercase()) {
        "HIGH" -> "High confidence"
        "MEDIUM" -> "Worth a look"
        "LOW" -> "Needs review"
        else -> band
    }

    /** Trims an ISO-8601 timestamp to a readable date; best-effort, never throws. */
    private fun prettyDate(iso: String): String =
        iso.substringBefore('T').ifBlank { iso }
}
