package com.example.echo.ui.share

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.echo.ui.components.MemoryCard
import com.example.echo.ui.components.ProcessingAnimation
import com.example.echo.ui.theme.BorderLight
import com.example.echo.ui.theme.CoralAlert
import com.example.echo.ui.theme.CoralLight
import com.example.echo.ui.theme.ForestGreen
import com.example.echo.ui.theme.MintGreen
import com.example.echo.ui.theme.MintGreenLight
import com.example.echo.ui.theme.OffWhiteBackground
import com.example.echo.ui.theme.PureWhite
import com.example.echo.ui.theme.SlateSurface
import com.example.echo.ui.theme.TextMuted
import com.example.echo.ui.theme.TextPrimary
import com.example.echo.ui.theme.TextSecondary

@Composable
fun ShareScreen(
    payload: SharedPayload?,
    state: ShareUiState,
    modifier: Modifier = Modifier,
    onSubmit: (note: String?) -> Unit,
    onRetry: () -> Unit,
    onDone: () -> Unit,
) {
    Box(modifier = Modifier.fillMaxSize().background(OffWhiteBackground)) {
        Column(
            modifier = modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
        ) {
            when (state) {
                is ShareUiState.Idle ->
                    if (payload == null) {
                        NothingToSave(onDone)
                    } else {
                        CaptureForm(payload = payload, onSubmit = onSubmit)
                    }

                is ShareUiState.Working -> WorkingView(state.message)

                is ShareUiState.Ready -> {
                    Text(
                        if (state.wasDuplicate) "✨ Already Saved" else "🎉 Saved to Echo!",
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Bold,
                        color = ForestGreen
                    )
                    Spacer(Modifier.height(16.dp))
                    MemoryCard(state.memory)
                    Spacer(Modifier.height(24.dp))
                    Button(
                        onClick = onDone,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = MintGreen, contentColor = PureWhite)
                    ) { Text("Done", fontWeight = FontWeight.Bold) }
                }

                is ShareUiState.Failure -> FailureView(
                    message = state.message,
                    hint = state.hint,
                    onRetry = onRetry,
                    onDone = onDone,
                )
            }
        }
    }
}

@Composable
private fun CaptureForm(payload: SharedPayload, onSubmit: (String?) -> Unit) {
    var note by remember { mutableStateOf("") }

    Text(
        "Save to Echo",
        style = MaterialTheme.typography.headlineMedium,
        fontWeight = FontWeight.Bold,
        color = ForestGreen
    )
    Spacer(Modifier.height(4.dp))
    Text(
        "Extracting intention and setting up intelligent resurfacing…",
        style = MaterialTheme.typography.bodyMedium,
        color = TextSecondary
    )
    Spacer(Modifier.height(20.dp))

    Card(
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = PureWhite),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        border = BorderStroke(1.dp, BorderLight)
    ) {
        Column(Modifier.padding(16.dp)) {
            when (payload) {
                is SharedPayload.Text -> Text(
                    payload.content,
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 6,
                    color = TextPrimary
                )

                is SharedPayload.Image -> {
                    AsyncImage(
                        model = payload.uri,
                        contentDescription = "Shared image",
                        modifier = Modifier.fillMaxWidth().height(200.dp),
                    )
                    Spacer(Modifier.height(12.dp))
                    Text("📷 Image Captured", style = MaterialTheme.typography.labelSmall, color = ForestGreen)
                }
            }
        }
    }

    Spacer(Modifier.height(20.dp))
    OutlinedTextField(
        value = note,
        onValueChange = { note = it },
        placeholder = { Text("Add personal context or notes (optional)…", color = TextMuted) },
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = MintGreen,
            unfocusedBorderColor = BorderLight,
            focusedContainerColor = PureWhite,
            unfocusedContainerColor = SlateSurface.copy(alpha = 0.5f)
        )
    )
    Spacer(Modifier.height(24.dp))
    Button(
        onClick = { onSubmit(note.trim().ifBlank { null }) },
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = ButtonDefaults.buttonColors(containerColor = MintGreen, contentColor = PureWhite)
    ) { Text("Save Memory", fontWeight = FontWeight.Bold) }
}

@Composable
private fun WorkingView(message: String) {
    Column(
        modifier = Modifier.fillMaxSize().padding(top = 80.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        ProcessingAnimation(message)
    }
}

@Composable
private fun FailureView(message: String, hint: String?, onRetry: () -> Unit, onDone: () -> Unit) {
    Text("Couldn't Save", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold, color = CoralAlert)
    Spacer(Modifier.height(8.dp))
    Text(message, style = MaterialTheme.typography.bodyLarge, color = TextPrimary)
    hint?.takeIf { it.isNotBlank() }?.let {
        Spacer(Modifier.height(6.dp))
        Text(it, style = MaterialTheme.typography.bodyMedium, color = TextSecondary)
    }
    Spacer(Modifier.height(24.dp))
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Button(
            onClick = onRetry,
            shape = RoundedCornerShape(10.dp),
            colors = ButtonDefaults.buttonColors(containerColor = MintGreen, contentColor = PureWhite)
        ) { Text("Try Again") }
        OutlinedButton(
            onClick = onDone,
            shape = RoundedCornerShape(10.dp),
            border = BorderStroke(1.dp, BorderLight),
            colors = ButtonDefaults.outlinedButtonColors(contentColor = TextPrimary)
        ) { Text("Cancel") }
    }
}

@Composable
private fun NothingToSave(onDone: () -> Unit) {
    Text("Nothing to Save", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold, color = TextPrimary)
    Spacer(Modifier.height(8.dp))
    Text(
        "No shared content was detected. Please share a link or text from another app to Echo.",
        style = MaterialTheme.typography.bodyLarge,
        color = TextSecondary
    )
    Spacer(Modifier.height(24.dp))
    Button(
        onClick = onDone,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = ButtonDefaults.buttonColors(containerColor = MintGreen, contentColor = PureWhite)
    ) { Text("Close") }
}

