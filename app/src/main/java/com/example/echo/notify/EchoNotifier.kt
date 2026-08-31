package com.example.echo.notify

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.example.echo.MainActivity
import com.example.echo.R
import com.example.echo.data.NotificationDto

/**
 * Turns a backend [NotificationDto] into a real system notification. Tapping it
 * opens [MainActivity] focused on the memory (via [MainActivity.EXTRA_MEMORY_ID]).
 *
 * No secrets, no push infra - this is the device end of the polling pipeline.
 */
object EchoNotifier {

    /** High-importance channel for the actual resurfacing alerts (§22). */
    const val CHANNEL_ALERTS = "echo_resurfacing"

    /** Low-importance channel for the persistent "watching" foreground notice. */
    const val CHANNEL_SERVICE = "echo_service"

    /** Fixed id for the foreground-service notice (only ever one). */
    const val SERVICE_NOTIFICATION_ID = 1

    fun ensureChannels(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService(NotificationManager::class.java) ?: return
        manager.createNotificationChannel(
            NotificationChannel(
                CHANNEL_ALERTS,
                "Resurfacing",
                NotificationManager.IMPORTANCE_HIGH,
            ).apply { description = "Echo resurfacing a forgotten intention." }
        )
        manager.createNotificationChannel(
            NotificationChannel(
                CHANNEL_SERVICE,
                "Echo background watch",
                NotificationManager.IMPORTANCE_LOW,
            ).apply { description = "Echo is watching for resurfacing moments." }
        )
    }

    /** Builds the persistent notice the foreground service must display. */
    fun serviceNotification(context: Context): android.app.Notification {
        ensureChannels(context)
        return NotificationCompat.Builder(context, CHANNEL_SERVICE)
            .setContentTitle("Echo is watching")
            .setContentText("Listening for forgotten intentions.")
            .setSmallIcon(R.mipmap.ic_launcher)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setContentIntent(openAppIntent(context, memoryId = null, requestCode = 0))
            .build()
    }

    /** Posts a resurfacing alert. No-op if POST_NOTIFICATIONS is not granted. */
    fun notify(context: Context, dto: NotificationDto) {
        if (!hasPermission(context)) return
        ensureChannels(context)

        val notification = NotificationCompat.Builder(context, CHANNEL_ALERTS)
            .setContentTitle(dto.title)
            .setContentText(dto.body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(dto.body))
            .setSmallIcon(R.mipmap.ic_launcher)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(
                openAppIntent(context, memoryId = dto.memoryId, requestCode = dto.id.hashCode())
            )
            .build()

        NotificationManagerCompat.from(context).notify(dto.id.hashCode(), notification)
    }

    private fun openAppIntent(
        context: Context,
        memoryId: String?,
        requestCode: Int,
    ): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            if (memoryId != null) putExtra(MainActivity.EXTRA_MEMORY_ID, memoryId)
        }
        return PendingIntent.getActivity(
            context,
            requestCode,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    private fun hasPermission(context: Context): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return true
        return ContextCompat.checkSelfPermission(
            context, Manifest.permission.POST_NOTIFICATIONS
        ) == PackageManager.PERMISSION_GRANTED
    }
}
