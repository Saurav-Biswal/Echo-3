package com.example.echo

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.echo.ui.share.ShareScreen
import com.example.echo.ui.share.ShareViewModel
import com.example.echo.ui.share.SharedPayload
import com.example.echo.ui.theme.EchoTheme

/**
 * Receives content from any app's share sheet (ACTION_SEND) and runs it through
 * the Echo loop: SAVE -> UNDERSTAND -> show the memory card. This is the app's
 * primary entry point (§23-26).
 */
class ShareActivity : ComponentActivity() {

    private val viewModel: ShareViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val payload = parsePayload(intent)

        setContent {
            EchoTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    Scaffold { inner ->
                        val state by viewModel.state.collectAsStateWithLifecycle()
                        ShareScreen(
                            payload = payload,
                            state = state,
                            modifier = Modifier.padding(inner),
                            onSubmit = { note -> submit(payload, note) },
                            onRetry = viewModel::retry,
                            onDone = { finish() },
                        )
                    }
                }
            }
        }
    }

    private fun submit(payload: SharedPayload?, note: String?) {
        when (payload) {
            is SharedPayload.Text ->
                viewModel.submitText(payload.content, payload.inputType, note)

            is SharedPayload.Image -> {
                val bytes = readBytes(payload.uri)
                if (bytes == null) {
                    // Nothing to send; the screen will surface the failure state
                    // on next submit. Fall back to reporting via text path is not
                    // possible, so we no-op here and let the user retry/dismiss.
                    return
                }
                viewModel.submitImage(
                    bytes = bytes,
                    fileName = payload.fileName,
                    mimeType = payload.mimeType,
                    note = note,
                )
            }

            null -> Unit
        }
    }

    private fun readBytes(uri: Uri): ByteArray? =
        try {
            contentResolver.openInputStream(uri)?.use { it.readBytes() }
        } catch (e: Exception) {
            null
        }

    private fun parsePayload(intent: Intent?): SharedPayload? {
        if (intent?.action != Intent.ACTION_SEND) return null
        val type = intent.type.orEmpty()

        if (type.startsWith("text/")) {
            val text = intent.getStringExtra(Intent.EXTRA_TEXT)?.trim().orEmpty()
            if (text.isEmpty()) return null
            return SharedPayload.Text(content = text, inputType = inputTypeFor(text))
        }

        if (type.startsWith("image/")) {
            @Suppress("DEPRECATION")
            val uri = intent.getParcelableExtra<Uri>(Intent.EXTRA_STREAM) ?: return null
            val name = uri.lastPathSegment?.substringAfterLast('/') ?: "shared_image"
            return SharedPayload.Image(uri = uri, fileName = name, mimeType = type)
        }

        return null
    }

    private fun inputTypeFor(text: String): String {
        val looksLikeUrl = text.none { it.isWhitespace() } &&
            (text.startsWith("http://") || text.startsWith("https://"))
        return if (looksLikeUrl) "url" else "text"
    }
}
