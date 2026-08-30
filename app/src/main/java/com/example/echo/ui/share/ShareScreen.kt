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
import com.example.echo.ui.components.ScanlineEffect
import com.example.echo.ui.theme.AcidGreen
import com.example.echo.ui.theme.BaseBlack
import com.example.echo.ui.theme.DarkGrey

@Composable
fun ShareScreen(
    payload: SharedPayload?,
    state: ShareUiState,
    modifier: Modifier = Modifier,
    onSubmit: (note: String?) -> Unit,
    onRetry: () -> Unit,
    onDone: () -> Unit,
) {
    Box(modifier = Modifier.fillMaxSize().background(BaseBlack)) {
        ScanlineEffect()
        
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
                        if (state.wasDuplicate) "// DUPLICATE_FOUND" else "// MEMORY_RECOVERED",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = AcidGreen
                    )
                    Spacer(Modifier.height(20.dp))
                    MemoryCard(state.memory)
                    Spacer(Modifier.height(24.dp))
                    Button(
                        onClick = onDone, 
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(0.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = AcidGreen, contentColor = Color.Black)
                    ) { Text("CLOSE_LOG") }
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
        "SIGNAL_INTERCEPT",
        style = MaterialTheme.typography.headlineSmall,
        fontWeight = FontWeight.Bold,
        color = AcidGreen
    )
    Spacer(Modifier.height(4.dp))
    Text(
        "EXTRACTING INTENTION FROM EXTERNAL DATA STREAM...",
        style = MaterialTheme.typography.labelSmall,
        color = Color.Gray,
        letterSpacing = 1.sp
    )
    Spacer(Modifier.height(24.dp))

    Card(
        shape = RoundedCornerShape(0.dp), 
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = DarkGrey),
        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.1f))
    ) {
        Column(Modifier.padding(16.dp)) {
            when (payload) {
                is SharedPayload.Text -> Text(
                    payload.content,
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 6,
                    color = Color.White,
                    fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace
                )

                is SharedPayload.Image -> {
                    AsyncImage(
                        model = payload.uri,
                        contentDescription = "Shared image",
                        modifier = Modifier.fillMaxWidth().height(200.dp),
                    )
                    Spacer(Modifier.height(12.dp))
                    Text("IMAGE_DATA_PACKET", style = MaterialTheme.typography.labelSmall, color = AcidGreen)
                }
            }
        }
    }

    Spacer(Modifier.height(24.dp))
    OutlinedTextField(
        value = note,
        onValueChange = { note = it },
        label = { Text("ADD_CONTEXT_MANUALLY") },
        placeholder = { Text("INPUT_FIELD_01") },
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(0.dp),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = AcidGreen,
            unfocusedBorderColor = Color.Gray,
            focusedLabelColor = AcidGreen
        )
    )
    Spacer(Modifier.height(24.dp))
    Button(
        onClick = { onSubmit(note.trim().ifBlank { null }) },
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(0.dp),
        colors = ButtonDefaults.buttonColors(containerColor = AcidGreen, contentColor = Color.Black)
    ) { Text("START_RECOVERY_ENGINE") }
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
    Text("SYSTEM_FAILURE", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = Color.Red)
    Spacer(Modifier.height(12.dp))
    Text("ERROR_LOG: ${message.uppercase()}", style = MaterialTheme.typography.bodyLarge, color = Color.White)
    hint?.takeIf { it.isNotBlank() }?.let {
        Spacer(Modifier.height(8.dp))
        Text("SUGGESTED_FIX: ${it.uppercase()}", style = MaterialTheme.typography.bodyMedium, color = Color.Gray)
    }
    Spacer(Modifier.height(32.dp))
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Button(
            onClick = onRetry,
            shape = RoundedCornerShape(0.dp),
            colors = ButtonDefaults.buttonColors(containerColor = AcidGreen, contentColor = Color.Black)
        ) { Text("RETRY_SEQUENCE") }
        OutlinedButton(
            onClick = onDone,
            shape = RoundedCornerShape(0.dp),
            border = BorderStroke(1.dp, Color.White),
            colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White)
        ) { Text("ABORT") }
    }
}

@Composable
private fun NothingToSave(onDone: () -> Unit) {
    Text("NULL_PAYLOAD", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = AcidGreen)
    Spacer(Modifier.height(12.dp))
    Text(
        "NO DATA DETECTED IN THE INBOUND STREAM. INITIALIZE TRANSFER FROM SOURCE APP.",
        style = MaterialTheme.typography.bodyLarge,
        color = Color.White
    )
    Spacer(Modifier.height(32.dp))
    Button(
        onClick = onDone, 
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(0.dp),
        colors = ButtonDefaults.buttonColors(containerColor = AcidGreen, contentColor = Color.Black)
    ) { Text("CLOSE_PORT") }
}
