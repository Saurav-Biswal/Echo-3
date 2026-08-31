package com.example.echo.ui.home

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.echo.data.OverviewResponse
import com.example.echo.ui.components.MemoryCard
import com.example.echo.ui.theme.AmberLight
import com.example.echo.ui.theme.AmberWarning
import com.example.echo.ui.theme.BlueInfo
import com.example.echo.ui.theme.BlueLight
import com.example.echo.ui.theme.BorderLight
import com.example.echo.ui.theme.CoralAlert
import com.example.echo.ui.theme.CoralLight
import com.example.echo.ui.theme.ForestGreen
import com.example.echo.ui.theme.MintGreen
import com.example.echo.ui.theme.MintGreenBorder
import com.example.echo.ui.theme.MintGreenLight
import com.example.echo.ui.theme.OffWhiteBackground
import com.example.echo.ui.theme.PureWhite
import com.example.echo.ui.theme.SlateSurface
import com.example.echo.ui.theme.TextMuted
import com.example.echo.ui.theme.TextPrimary
import com.example.echo.ui.theme.TextSecondary

@Composable
fun HomeScreen(
    state: HomeUiState,
    captureStatus: String?,
    simStatus: String?,
    modifier: Modifier = Modifier,
    onCapture: (content: String, note: String?) -> Unit,
    onRetry: () -> Unit,
    onSimulateNearby: (String) -> Unit,
    onDelete: (String) -> Unit = {},
    onComplete: (String) -> Unit = {},
) {
    var showLaptopDialog by remember { mutableStateOf(false) }

    if (showLaptopDialog) {
        LaptopDashboardDialog(onDismiss = { showLaptopDialog = false })
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(OffWhiteBackground)
    ) {
        LazyColumn(
            modifier = modifier
                .fillMaxSize()
                .padding(horizontal = 20.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp),
        ) {
            // App Header Row with Laptop Dashboard button on top right
            item {
                Spacer(Modifier.height(16.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(10.dp)
                                    .clip(CircleShape)
                                    .background(MintGreen)
                            )
                            Spacer(Modifier.width(8.dp))
                            Text(
                                "Echo",
                                style = MaterialTheme.typography.headlineMedium,
                                fontWeight = FontWeight.ExtraBold,
                                color = ForestGreen
                            )
                        }
                        Text(
                            "Recovering forgotten intentions",
                            style = MaterialTheme.typography.labelSmall,
                            color = TextMuted
                        )
                    }

                    // Top-Right Laptop Dashboard Button
                    Row(
                        modifier = Modifier
                            .clip(RoundedCornerShape(20.dp))
                            .background(MintGreenLight)
                            .clickable { showLaptopDialog = true }
                            .padding(horizontal = 12.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("💻", fontSize = 14.sp)
                        Spacer(Modifier.width(6.dp))
                        Text(
                            "Laptop Dashboard",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = ForestGreen
                        )
                    }
                }
            }

            // Simulate Nearby status banner
            if (simStatus != null) {
                item {
                    Card(
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = AmberLight),
                        border = BorderStroke(1.dp, AmberWarning.copy(alpha = 0.4f))
                    ) {
                        Row(
                            modifier = Modifier.padding(14.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                simStatus,
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.Medium,
                                color = Color(0xFFB45309),
                            )
                        }
                    }
                }
            }

            when (state) {
                is HomeUiState.Loading -> item {
                    Column(
                        Modifier
                            .fillMaxWidth()
                            .padding(top = 64.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                    ) {
                        CircularProgressIndicator(color = MintGreen)
                        Spacer(Modifier.height(12.dp))
                        Text("Loading your intentions…", color = TextMuted, style = MaterialTheme.typography.bodyMedium)
                    }
                }

                is HomeUiState.Error -> item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = PureWhite),
                        border = BorderStroke(1.dp, CoralLight)
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(24.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Text(
                                "Unable to connect",
                                fontWeight = FontWeight.Bold,
                                color = CoralAlert,
                                style = MaterialTheme.typography.titleMedium
                            )
                            Spacer(Modifier.height(6.dp))
                            Text(
                                state.message,
                                color = TextSecondary,
                                style = MaterialTheme.typography.bodyMedium
                            )
                            Spacer(Modifier.height(16.dp))
                            Button(
                                onClick = onRetry,
                                colors = ButtonDefaults.buttonColors(containerColor = MintGreen, contentColor = PureWhite),
                                shape = RoundedCornerShape(10.dp)
                            ) {
                                Text("🔄 Retry Connection")
                            }
                        }
                    }
                }

                is HomeUiState.Loaded -> {
                    item { StatsRow(state.overview) }
                    item { CaptureBox(captureStatus = captureStatus, onCapture = onCapture) }

                    if (state.overview.recent.isEmpty()) {
                        item { EmptyHint() }
                    } else {
                        item {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    "Saved Intentions",
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.Bold,
                                    color = TextPrimary,
                                )
                                Text(
                                    "${state.overview.recent.size} items",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = TextMuted
                                )
                            }
                        }
                        items(state.overview.recent, key = { it.id }) { memory ->
                            MemoryCard(
                                memory = memory,
                                onSimulateNearby = onSimulateNearby,
                                onDelete = onDelete,
                                onComplete = onComplete,
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
        StatCard("Active", overview.active, Modifier.weight(1f), MintGreen, MintGreenLight)
        StatCard("Resurfaced", overview.resurfaced, Modifier.weight(1f), BlueInfo, BlueLight)
        StatCard(
            "Review",
            overview.needsReview,
            Modifier.weight(1f),
            if (overview.needsReview > 0) CoralAlert else TextMuted,
            if (overview.needsReview > 0) CoralLight else SlateSurface
        )
    }
}

@Composable
private fun StatCard(
    label: String,
    value: Int,
    modifier: Modifier = Modifier,
    accentColor: Color,
    bgColor: Color,
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = PureWhite),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        border = BorderStroke(1.dp, BorderLight)
    ) {
        Column(Modifier.padding(14.dp)) {
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .background(bgColor)
                    .padding(horizontal = 8.dp, vertical = 4.dp)
            ) {
                Text(
                    value.toString().padStart(2, '0'),
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.ExtraBold,
                    color = accentColor
                )
            }
            Spacer(Modifier.height(8.dp))
            Text(
                label,
                style = MaterialTheme.typography.labelSmall,
                color = TextSecondary,
                fontWeight = FontWeight.Medium
            )
        }
    }
}

@Composable
private fun CaptureBox(captureStatus: String?, onCapture: (String, String?) -> Unit) {
    var content by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }

    Card(
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = PureWhite),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        border = BorderStroke(1.dp, BorderLight)
    ) {
        Column(Modifier.padding(18.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    "✨ Save New Intention",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = ForestGreen
                )
            }
            Spacer(Modifier.height(14.dp))
            OutlinedTextField(
                value = content,
                onValueChange = { content = it },
                placeholder = { Text("Paste Instagram reel, TikTok, map link, or text note…", color = TextMuted) },
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = MintGreen,
                    unfocusedBorderColor = BorderLight,
                    focusedContainerColor = PureWhite,
                    unfocusedContainerColor = SlateSurface.copy(alpha = 0.5f)
                ),
                shape = RoundedCornerShape(12.dp)
            )
            Spacer(Modifier.height(10.dp))
            OutlinedTextField(
                value = note,
                onValueChange = { note = it },
                placeholder = { Text("Add personal context / note (optional)…", color = TextMuted) },
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = MintGreen,
                    unfocusedBorderColor = BorderLight,
                    focusedContainerColor = PureWhite,
                    unfocusedContainerColor = SlateSurface.copy(alpha = 0.5f)
                ),
                shape = RoundedCornerShape(12.dp)
            )
            Spacer(Modifier.height(16.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                captureStatus?.let {
                    Text(
                        it,
                        style = MaterialTheme.typography.labelSmall,
                        color = ForestGreen,
                        fontWeight = FontWeight.SemiBold
                    )
                } ?: Spacer(Modifier.height(1.dp))
                Button(
                    onClick = {
                        onCapture(content, note.trim().ifBlank { null })
                        content = ""
                        note = ""
                    },
                    enabled = content.isNotBlank(),
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MintGreen,
                        contentColor = PureWhite,
                        disabledContainerColor = SlateSurface,
                        disabledContentColor = TextMuted
                    )
                ) {
                    Text("Save Memory", fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
private fun EmptyHint() {
    Card(
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = PureWhite),
        border = BorderStroke(1.dp, BorderLight)
    ) {
        Column(
            Modifier.padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text("🌱 Ready for your saves", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = ForestGreen)
            Spacer(Modifier.height(8.dp))
            Text(
                "Save Instagram Reels, Google Maps links, or recipes to Echo. Echo will remind you at the perfect time and place.",
                style = MaterialTheme.typography.bodyMedium,
                color = TextSecondary,
                lineHeight = 20.sp
            )
        }
    }
}

@Composable
private fun LaptopDashboardDialog(onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("💻", fontSize = 20.sp)
                Spacer(Modifier.width(8.dp))
                Text("Laptop Dashboard", fontWeight = FontWeight.Bold, color = TextPrimary)
            }
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(
                    "You can access and manage your Echo memories directly on your laptop or any browser connected to your Wi-Fi.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary
                )

                Card(
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = MintGreenLight),
                    border = BorderStroke(1.dp, MintGreenBorder),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(Modifier.padding(14.dp)) {
                        Text(
                            "🌐 Dashboard URL (Next.js):",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = ForestGreen
                        )
                        Spacer(Modifier.height(4.dp))
                        Text(
                            "http://10.175.80.122:3000",
                            style = MaterialTheme.typography.bodyLarge,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                        Spacer(Modifier.height(10.dp))
                        Text(
                            "⚡ Backend API Docs:",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = ForestGreen
                        )
                        Spacer(Modifier.height(4.dp))
                        Text(
                            "http://10.175.80.122:8000/docs",
                            style = MaterialTheme.typography.bodyMedium,
                            color = TextSecondary
                        )
                    }
                }

                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(8.dp)
                            .clip(CircleShape)
                            .background(MintGreen)
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        "Status: Live & Synced over Wi-Fi",
                        style = MaterialTheme.typography.labelSmall,
                        color = ForestGreen,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
        },
        confirmButton = {
            Button(
                onClick = onDismiss,
                colors = ButtonDefaults.buttonColors(containerColor = MintGreen, contentColor = PureWhite),
                shape = RoundedCornerShape(8.dp)
            ) { Text("Got it") }
        },
        containerColor = PureWhite,
        shape = RoundedCornerShape(20.dp)
    )
}
