package com.example.echo.notify

import android.Manifest
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
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
 * a system notification for each new one. Also continuously samples the device's
 * GPS/network location so the backend can evaluate real-world geofences (§19).
 */
class NotificationPoller : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val repo = EchoRepository()
    private lateinit var seen: SeenStore
    private var polling = false
    private var lastLocation: Location? = null

    private val locationListener = object : LocationListener {
        override fun onLocationChanged(location: Location) {
            lastLocation = location
        }
        override fun onProviderEnabled(provider: String) {}
        override fun onProviderDisabled(provider: String) {}
        @Deprecated("Deprecated in Java")
        override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        seen = SeenStore(applicationContext)
        EchoNotifier.ensureChannels(applicationContext)
        startLocationUpdates()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForegroundNotice()
        startLocationUpdates()
        if (!polling) {
            polling = true
            scope.launch { pollLoop() }
        }
        return START_STICKY
    }

    private fun startForegroundNotice() {
        val notification = EchoNotifier.serviceNotification(applicationContext)
        val type =
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC or ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION
            } else {
                0
            }
        ServiceCompat.startForeground(
            this, EchoNotifier.SERVICE_NOTIFICATION_ID, notification, type
        )
    }

    private fun startLocationUpdates() {
        if (!hasLocationPermission()) return
        try {
            val lm = getSystemService(LocationManager::class.java) ?: return
            val providers = listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)
            for (provider in providers) {
                if (lm.isProviderEnabled(provider)) {
                    val last = lm.getLastKnownLocation(provider)
                    if (last != null && (lastLocation == null || last.time > lastLocation!!.time)) {
                        lastLocation = last
                    }
                    lm.requestLocationUpdates(provider, 10_000L, 5f, locationListener)
                }
            }
        } catch (_: Exception) {
            // Location may be disabled or restricted by OS
        }
    }

    private fun hasLocationPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            this, Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED || ContextCompat.checkSelfPermission(
            this, Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun getBestLocation(): Pair<Double, Double>? {
        if (!hasLocationPermission()) return null
        try {
            val lm = getSystemService(LocationManager::class.java)
            if (lm != null) {
                val providers = listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)
                for (provider in providers) {
                    if (lm.isProviderEnabled(provider)) {
                        val loc = lm.getLastKnownLocation(provider)
                        if (loc != null && (lastLocation == null || loc.time > lastLocation!!.time)) {
                            lastLocation = loc
                        }
                    }
                }
            }
        } catch (_: Exception) {}
        return lastLocation?.let { it.latitude to it.longitude }
    }

    private suspend fun pollLoop() {
        while (scope.isActive) {
            try {
                val coords = getBestLocation()
                repo.notifications(
                    status = "SENT",
                    latitude = coords?.first,
                    longitude = coords?.second,
                ).onSuccess { page ->
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
        try {
            val lm = getSystemService(LocationManager::class.java)
            lm?.removeUpdates(locationListener)
        } catch (_: Exception) {}
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

