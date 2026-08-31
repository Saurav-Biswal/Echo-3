package com.example.echo.ui.home

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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import com.example.echo.data.OverviewResponse
import com.example.echo.ui.components.MemoryCard
import com.example.echo.ui.components.ScanlineEffect
import com.example.echo.ui.theme.AcidGreen
import com.example.echo.ui.theme.BaseBlack
import com.example.echo.ui.theme.DarkGrey

@Composable
fun HomeScreen(
    state: HomeUiState,
    captureStatus: String?,
    simStatus: String?,
    modifier: Modifier = Modifier,
    onCapture: (content: String, note: String?) -> Unit,
    onRetry: () -> Unit,
    onSimulateNearby: (String) -> Unit,
) {
    Box(modifier = Modifier.fillMaxSize().background(BaseBlack)) {
        ScanlineEffect()
        
        LazyColumn(
            modifier = modifier.fillMaxSize().padding(horizontal = 20.dp),
            verticalArrangement = Arrangement.spacedBy(24.dp),
        ) {
            item {
                Spacer(Modifier.height(24.dp))
                Text(
                    "ECHO // MEMORY_ENGINE", 
                    style = MaterialTheme.typography.headlineMedium, 
                    fontWeight = FontWeight.Bold,
                    color = AcidGreen
                )
                Text(
                    "RECOVERING FORGOTTEN INTENTIONS.",
                    style = MaterialTheme.typography.labelSmall,
                    color = Color.Gray,
                    letterSpacing = 2.sp
                )
            }

            // Simulate Nearby status banner
            if (simStatus != null) {
                item {
                    Card(
                        shape = RoundedCornerShape(0.dp),
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A00)),
                        border = BorderStroke(1.dp, Color(0xFFFFAB00).copy(alpha = 0.5f))
                    ) {
                        Text(
                            simStatus.uppercase(),
                            modifier = Modifier.padding(12.dp),
                            style = MaterialTheme.typography.labelSmall,
                            color = Color(0xFFFFAB00),
                        )
                    }
                }
            }

            when (state) {
                is HomeUiState.Loading -> item {
                    Column(
                        Modifier.fillMaxWidth().padding(top = 48.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                    ) { CircularProgressIndicator(color = AcidGreen) }
                }

                is HomeUiState.Error -> item {
                    Column(
                        modifier = Modifier.fillMaxWidth().background(DarkGrey).padding(16.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text("CONNECTION_ERROR: ${state.message.uppercase()}", color = Color.Red, style = MaterialTheme.typography.labelSmall)
                        Spacer(Modifier.height(16.dp))
                        Button(
                            onClick = onRetry,
                            colors = ButtonDefaults.buttonColors(containerColor = AcidGreen, contentColor = Color.Black),
                            shape = RoundedCornerShape(0.dp)
                        ) { Text("RETRY_CONNECTION") }
                    }
                }

                is HomeUiState.Loaded -> {
                    item { StatsRow(state.overview) }
                    item { CaptureBox(captureStatus = captureStatus, onCapture = onCapture) }
                    
                    if (state.overview.recent.isEmpty()) {
                        item { EmptyHint() }
                    } else {
                        item {
                            Text(
                                "// RECENT_RECOVERIES",
                                style = MaterialTheme.typography.titleMedium,
                                color = AcidGreen,
                            )
                        }
                        items(state.overview.recent, key = { it.id }) { memory ->
                            MemoryCard(
                                memory = memory,
                                onSimulateNearby = onSimulateNearby,
                            )
                        }
                    }
                }
            }
            item { Spacer(Modifier.height(48.dp)) }
        }
    }
}


@Composable
private fun StatsRow(overview: OverviewResponse) {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
        StatCard("ACTIVE", overview.active, Modifier.weight(1f))
        StatCard("RESURFACED", overview.resurfaced, Modifier.weight(1f))
        StatCard("REVIEW", overview.needsReview, Modifier.weight(1f), isAlert = overview.needsReview > 0)
    }
}

@Composable
private fun StatCard(label: String, value: Int, modifier: Modifier = Modifier, isAlert: Boolean = false) {
    val color = if (isAlert) Color.Red else AcidGreen
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(0.dp),
        colors = CardDefaults.cardColors(
            containerColor = DarkGrey,
        ),
        border = BorderStroke(1.dp, color.copy(alpha = 0.5f))
    ) {
        Column(Modifier.padding(12.dp)) {
            Text(
                value.toString().padStart(2, '0'),
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
                color = color
            )
            Text(label, style = MaterialTheme.typography.labelSmall, color = color.copy(alpha = 0.7f))
        }
    }
}

@Composable
private fun CaptureBox(captureStatus: String?, onCapture: (String, String?) -> Unit) {
    var content by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }

    Card(
        shape = RoundedCornerShape(0.dp), 
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = DarkGrey),
        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.1f))
    ) {
        Column(Modifier.padding(16.dp)) {
            Text("SIGNAL_INTERCEPT", style = MaterialTheme.typography.labelSmall, color = AcidGreen)
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(
                value = content,
                onValueChange = { content = it },
                label = { Text("PASTE_INTENTION (LINK/TEXT)") },
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = AcidGreen,
                    unfocusedBorderColor = Color.Gray,
                    focusedLabelColor = AcidGreen
                ),
                shape = RoundedCornerShape(0.dp)
            )
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(
                value = note,
                onValueChange = { note = it },
                label = { Text("ADD_CONTEXT (OPTIONAL)") },
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = AcidGreen,
                    unfocusedBorderColor = Color.Gray,
                    focusedLabelColor = AcidGreen
                ),
                shape = RoundedCornerShape(0.dp)
            )
            Spacer(Modifier.height(16.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                captureStatus?.let {
                    Text(it.uppercase(), style = MaterialTheme.typography.labelSmall, color = AcidGreen)
                } ?: Spacer(Modifier.height(1.dp))
                Button(
                    onClick = {
                        onCapture(content, note.trim().ifBlank { null })
                        content = ""
                        note = ""
                    },
                    enabled = content.isNotBlank(),
                    shape = RoundedCornerShape(0.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = AcidGreen,
                        contentColor = Color.Black,
                        disabledContainerColor = Color.DarkGray
                    )
                ) { Text("RECOVER_INTENTION") }
            }
        }
    }
}

@Composable
private fun EmptyHint() {
    Card(
        shape = RoundedCornerShape(0.dp), 
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = DarkGrey),
        border = BorderStroke(1.dp, AcidGreen.copy(alpha = 0.2f))
    ) {
        Column(Modifier.padding(20.dp)) {
            Text("ENGINE_IDLE", style = MaterialTheme.typography.labelSmall, color = AcidGreen)
            Spacer(Modifier.height(8.dp))
            Text(
                "NO INTENTIONS RECOVERED FROM THE DIGITAL VOID. SHARE DATA TO INITIALIZE.",
                style = MaterialTheme.typography.bodyMedium,
                color = Color.Gray
            )
            Spacer(Modifier.height(16.dp))
            TextButton(onClick = {}) { 
                Text("SYSTEM_TIP: USE SHARE_SHEET -> SAVE_TO_ECHO", color = AcidGreen, style = MaterialTheme.typography.labelSmall) 
            }
        }
    }
}
