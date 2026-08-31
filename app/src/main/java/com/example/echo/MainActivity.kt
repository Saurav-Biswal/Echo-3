package com.example.echo

import android.Manifest
import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.echo.notify.EchoNotifier
import com.example.echo.notify.NotificationPoller
import com.example.echo.ui.components.MemoryCard
import com.example.echo.ui.home.HomeScreen
import com.example.echo.ui.home.HomeViewModel
import com.example.echo.ui.theme.AcidGreen
import com.example.echo.ui.theme.BaseBlack
import com.example.echo.ui.theme.EchoTheme

/** Dashboard entry point: overview counts, recent memories, and inline save. */
class MainActivity : ComponentActivity() {

    private val viewModel: HomeViewModel by viewModels()

    private val requestNotificationPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { /* best effort */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        EchoNotifier.ensureChannels(this)
        maybeRequestNotificationPermission()
        NotificationPoller.start(this)
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
                        val focused by viewModel.focusedMemory.collectAsStateWithLifecycle()
                        LaunchedEffect(Unit) { viewModel.refresh() }
                        HomeScreen(
                            state = state,
                            captureStatus = captureStatus,
                            modifier = Modifier.padding(inner),
                            onCapture = viewModel::captureText,
                            onRetry = viewModel::refresh,
                        )
                        focused?.let { memory ->
                            Dialog(onDismissRequest = viewModel::dismissFocused) {
                                Surface(color = BaseBlack) {
                                    Column(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .background(BaseBlack)
                                            .verticalScroll(rememberScrollState())
                                            .padding(16.dp),
                                        verticalArrangement = Arrangement.spacedBy(12.dp),
                                    ) {
                                        Text(
                                            "// RESURFACED_INTENTION",
                                            style = MaterialTheme.typography.labelSmall,
                                            color = AcidGreen,
                                        )
                                        MemoryCard(memory)
                                        Column(
                                            Modifier.fillMaxWidth(),
                                            horizontalAlignment = Alignment.End,
                                        ) {
                                            TextButton(onClick = viewModel::dismissFocused) {
                                                Text("CLOSE", color = AcidGreen)
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

    private fun maybeRequestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requestNotificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    companion object {
        const val EXTRA_MEMORY_ID = "com.example.echo.MEMORY_ID"
    }
}
