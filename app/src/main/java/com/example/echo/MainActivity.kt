package com.example.echo

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.echo.ui.home.HomeScreen
import com.example.echo.ui.home.HomeViewModel
import com.example.echo.ui.theme.EchoTheme

/** Dashboard entry point: overview counts, recent memories, and inline save. */
class MainActivity : ComponentActivity() {

    private val viewModel: HomeViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            EchoTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    Scaffold { inner ->
                        val state by viewModel.state.collectAsStateWithLifecycle()
                        val captureStatus by viewModel.captureStatus.collectAsStateWithLifecycle()
                        LaunchedEffect(Unit) { viewModel.refresh() }
                        HomeScreen(
                            state = state,
                            captureStatus = captureStatus,
                            modifier = Modifier.padding(inner),
                            onCapture = viewModel::captureText,
                            onRetry = viewModel::refresh,
                        )
                    }
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // Reflect memories saved via the share sheet while we were backgrounded.
        viewModel.refresh()
    }
}
