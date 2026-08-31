package com.example.echo.notify

import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import com.example.echo.data.EchoRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * Foreground service that polls the backend's SENT notification feed and raises
 * a system notification for each new one. This is the device end of the
 * resurfacing pipeline: the backend's scan loop creates Notification rows; this
 * service is what actually reaches the user's status bar.
 *
 * Polling (not FCM) is deliberate - this build talks to the backend over an
 * `adb reverse` tunnel with no push credentials and no internet-reachable
 * server (secrets stay on the backend). See the plan for the tradeoff.
 */
class NotificationPoller : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val repo = EchoRepository()
    private lateinit var seen: SeenStore
    private var polling = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        seen = SeenStore(applicationContext)
        EchoNotifier.ensureChannels(applicationContext)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForegroundNotice()
        if (!polling) {
            polling = true
            scope.launch { pollLoop() }
        }
        // Restart if killed - the whole point is to keep watching.
        return START_STICKY
    }

    private fun startForegroundNotice() {
        val notification = EchoNotifier.serviceNotification(applicationContext)
        val type =
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            } else {
                0
            }
        ServiceCompat.startForeground(
            this, EchoNotifier.SERVICE_NOTIFICATION_ID, notification, type
        )
    }

    private suspend fun pollLoop() {
        while (scope.isActive) {
            try {
                repo.notifications(status = "SENT").onSuccess { page ->
                    for (dto in page.items) {
                        if (!seen.isSeen(dto.id)) {
                            EchoNotifier.notify(applicationContext, dto)
                            seen.markSeen(dto.id)
                        }
                    }
                }
            } catch (_: Exception) {
                // Backend unreachable is normal (tunnel down); try again next tick.
            }
            delay(POLL_MS)
        }
    }

    override fun onDestroy() {
        polling = false
        scope.cancel()
        super.onDestroy()
    }

    companion object {
        private const val POLL_MS = 15_000L

        fun start(context: Context) {
            val intent = Intent(context, NotificationPoller::class.java)
            ContextCompat.startForegroundService(context, intent)
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, NotificationPoller::class.java))
        }
    }
}
