package com.example.echo.notify

import android.content.Context

/**
 * Remembers which notifications the device has already raised, so re-polling the
 * SENT feed doesn't spam a duplicate every 30s. The server keeps a notification
 * SENT until the user acts on it, so dedupe must live on the device - ack-ing
 * would wrongly flip its status to ACTED before the user did anything (§22).
 */
class SeenStore(context: Context) {

    private val prefs =
        context.getSharedPreferences("echo_seen_notifications", Context.MODE_PRIVATE)

    fun isSeen(id: String): Boolean = prefs.getStringSet(KEY, emptySet())!!.contains(id)

    fun markSeen(id: String) {
        val current = prefs.getStringSet(KEY, emptySet())!!.toMutableSet()
        if (current.add(id)) {
            prefs.edit().putStringSet(KEY, current).apply()
        }
    }

    private companion object {
        const val KEY = "seen_ids"
    }
}
