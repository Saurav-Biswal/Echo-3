package com.example.echo

import android.Manifest
import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.echo.notify.EchoNotifier
import com.example.echo.notify.NotificationPoller
import com.example.echo.ui.components.MemoryCard
import com.example.echo.ui.home.HomeScreen
import com.example.echo.ui.home.HomeViewModel
import com.example.echo.ui.theme.EchoTheme
import com.example.echo.ui.theme.ForestGreen
import com.example.echo.ui.theme.PureWhite
import com.example.echo.ui.theme.TextSecondary

/** Dashboard entry point: overview counts, recent memories, and inline save. */
class MainActivity : ComponentActivity() {

    private val viewModel: HomeViewModel by viewModels()

    private val requestPermissions =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { results ->
            // If the user granted notifications, ensure the channel is registered.
            if (results[Manifest.permission.POST_NOTIFICATIONS] == true) {
                EchoNotifier.ensureChannels(this)
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Ensure notification channels exist before starting the foreground service
        EchoNotifier.ensureChannels(this)

        // Kick off the background poller service
        NotificationPoller.start(this)

        maybeRequestPermissions()
        handleIntent(intent)

        setContent {
            EchoTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    Scaffold { inner ->
                        val state by viewModel.state.collectAsStateWithLifecycle()
                        val captureStatus by viewModel.captureStatus.collectAsStateWithLifecycle()
                        val simStatus by viewModel.simStatus.collectAsStateWithLifecycle()
                        val focused by viewModel.focusedMemory.collectAsStateWithLifecycle()
                        LaunchedEffect(Unit) { viewModel.refresh() }

                        HomeScreen(
                            state = state,
                            captureStatus = captureStatus,
                            simStatus = simStatus,
                            modifier = Modifier.padding(inner),
                            onCapture = viewModel::captureText,
                            onRetry = viewModel::refresh,
                            onSimulateNearby = viewModel::simulateNearby,
                            onDelete = viewModel::deleteMemory,
                            onComplete = viewModel::completeMemory,
                        )

                        focused?.let { memory ->
                            Dialog(onDismissRequest = viewModel::dismissFocused) {
                                Surface(
                                    shape = RoundedCornerShape(20.dp),
                                    color = PureWhite,
                                    shadowElevation = 8.dp,
                                ) {
                                    Column(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .verticalScroll(rememberScrollState())
                                            .padding(20.dp),
                                        verticalArrangement = Arrangement.spacedBy(16.dp),
                                    ) {
                                        Text(
                                            "📍 Resurfaced Intention",
                                            style = MaterialTheme.typography.titleMedium,
                                            fontWeight = FontWeight.Bold,
                                            color = ForestGreen,
                                        )
                                        MemoryCard(
                                            memory = memory,
                                            onSimulateNearby = null,
                                            onDelete = viewModel::deleteMemory,
                                            onComplete = viewModel::completeMemory,
                                        )
                                        Column(
                                            Modifier.fillMaxWidth(),
                                            horizontalAlignment = Alignment.End,
                                        ) {
                                            TextButton(onClick = viewModel::dismissFocused) {
                                                Text("Dismiss", color = TextSecondary)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }

    override fun onResume() {
        super.onResume()
        // Reflect memories saved via the share sheet while we were backgrounded.
        viewModel.refresh()
    }

    /** A notification tap arrives with the memory id; surface that memory. */
    private fun handleIntent(intent: Intent?) {
        val memoryId = intent?.getStringExtra(EXTRA_MEMORY_ID)?.takeIf { it.isNotBlank() }
        if (memoryId != null) viewModel.openMemory(memoryId)
    }

    private fun maybeRequestPermissions() {
        val permissions = mutableListOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
        )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        requestPermissions.launch(permissions.toTypedArray())
    }

    companion object {
        const val EXTRA_MEMORY_ID = "com.example.echo.MEMORY_ID"
    }
}
