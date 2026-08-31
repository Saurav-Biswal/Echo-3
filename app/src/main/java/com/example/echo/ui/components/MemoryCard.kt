package com.example.echo.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.echo.data.MemoryDto
import com.example.echo.ui.ActionLauncher
import com.example.echo.ui.Display
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
import com.example.echo.ui.theme.PureWhite
import com.example.echo.ui.theme.SlateSurface
import com.example.echo.ui.theme.TextMuted
import com.example.echo.ui.theme.TextPrimary
import com.example.echo.ui.theme.TextSecondary

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun MemoryCard(
    memory: MemoryDto,
    modifier: Modifier = Modifier,
    onSimulateNearby: ((String) -> Unit)? = null,
    onDelete: ((String) -> Unit)? = null,
    onComplete: ((String) -> Unit)? = null,
) {
    val context = LocalContext.current
    var showDeleteConfirm by remember { mutableStateOf(false) }

    if (showDeleteConfirm) {
        AlertDialog(
            onDismissRequest = { showDeleteConfirm = false },
            title = { Text("Delete Memory", fontWeight = FontWeight.Bold, color = TextPrimary) },
            text = { Text("Are you sure you want to remove this saved memory? This cannot be undone.", color = TextSecondary) },
            confirmButton = {
                Button(
                    onClick = {
                        showDeleteConfirm = false
                        onDelete?.invoke(memory.id)
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = CoralAlert, contentColor = PureWhite),
                    shape = RoundedCornerShape(8.dp)
                ) { Text("Delete") }
            },
            dismissButton = {
                TextButton(onClick = { showDeleteConfirm = false }) {
                    Text("Cancel", color = TextSecondary)
                }
            },
            containerColor = PureWhite,
            shape = RoundedCornerShape(16.dp)
        )
    }

    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = PureWhite),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        border = BorderStroke(1.dp, BorderLight)
    ) {
        Column(Modifier.padding(20.dp)) {
            // Header Row: Category Badge + Status / Delete
            Row(
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth()
            ) {
                // Category Chip
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier
                        .clip(RoundedCornerShape(20.dp))
                        .background(MintGreenLight)
                        .padding(horizontal = 10.dp, vertical = 5.dp)
                ) {
                    Text(
                        "${Display.categoryEmoji(memory.category)} ${Display.categoryLabel(memory.category)}",
                        style = MaterialTheme.typography.labelSmall,
                        color = ForestGreen,
                        fontWeight = FontWeight.SemiBold
                    )
                }

                Row(verticalAlignment = Alignment.CenterVertically) {
                    // Status Badge
                    val statusColor = when (memory.status) {
                        "COMPLETED" -> ForestGreen
                        "RESURFACED" -> BlueInfo
                        "NEEDS_REVIEW" -> CoralAlert
                        else -> MintGreen
                    }
                    val statusBg = when (memory.status) {
                        "COMPLETED" -> MintGreenLight
                        "RESURFACED" -> BlueLight
                        "NEEDS_REVIEW" -> CoralLight
                        else -> SlateSurface
                    }

                    Text(
                        text = memory.status.replace("_", " "),
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = statusColor,
                        modifier = Modifier
                            .clip(RoundedCornerShape(12.dp))
                            .background(statusBg)
                            .padding(horizontal = 8.dp, vertical = 3.dp)
                    )

                    if (onDelete != null) {
                        Spacer(Modifier.width(8.dp))
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(8.dp))
                                .clickable { showDeleteConfirm = true }
                                .padding(horizontal = 6.dp, vertical = 4.dp)
                        ) {
                            Text("🗑️", fontSize = 14.sp)
                        }
                    }
                }
            }

            Spacer(Modifier.height(12.dp))

            // Title
            Text(
                text = Display.cardTitle(memory),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = TextPrimary
            )

            // Summary (if distinct)
            memory.summary?.takeIf { it.isNotBlank() && it != memory.title }?.let {
                Spacer(Modifier.height(6.dp))
                Text(
                    text = it,
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary,
                    lineHeight = 20.sp
                )
            }

            // Why you saved this: highlight card
            Spacer(Modifier.height(14.dp))
            Card(
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = MintGreenLight.copy(alpha = 0.6f)),
                border = BorderStroke(1.dp, MintGreenBorder.copy(alpha = 0.5f)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(Modifier.padding(12.dp)) {
                    Text(
                        "💡 Why you saved this",
                        style = MaterialTheme.typography.labelSmall,
                        color = ForestGreen,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        text = memory.whySaved,
                        style = MaterialTheme.typography.bodyMedium,
                        color = TextPrimary
                    )
                }
            }

            // When / Resurfacing line
            val whenText = Display.whenLine(memory.triggers)
            if (whenText.isNotBlank()) {
                Spacer(Modifier.height(12.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("📍", fontSize = 13.sp)
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = whenText,
                        style = MaterialTheme.typography.bodySmall,
                        color = TextSecondary
                    )
                }
            }

            // Action Buttons
            val actions = Display.orderedActions(memory.actions)
            if (actions.isNotEmpty() || onComplete != null || onSimulateNearby != null) {
                Spacer(Modifier.height(16.dp))
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    actions.forEach { action ->
                        val enabled = Display.actionLink(action) != null
                        if (action.isPrimary) {
                            Button(
                                onClick = { ActionLauncher.launch(context, action) },
                                enabled = enabled,
                                shape = RoundedCornerShape(10.dp),
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = MintGreen,
                                    contentColor = PureWhite
                                )
                            ) {
                                Text(action.label, fontWeight = FontWeight.SemiBold)
                            }
                        } else {
                            OutlinedButton(
                                onClick = { ActionLauncher.launch(context, action) },
                                enabled = enabled,
                                shape = RoundedCornerShape(10.dp),
                                border = BorderStroke(1.dp, BorderLight),
                                colors = ButtonDefaults.outlinedButtonColors(contentColor = TextPrimary)
                            ) {
                                Text(action.label)
                            }
                        }
                    }

                    // Complete Action
                    if (onComplete != null && memory.status != "COMPLETED") {
                        OutlinedButton(
                            onClick = { onComplete(memory.id) },
                            shape = RoundedCornerShape(10.dp),
                            border = BorderStroke(1.dp, MintGreenBorder),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = ForestGreen)
                        ) {
                            Text("✓ Complete", fontWeight = FontWeight.Medium)
                        }
                    }

                    // Simulate Nearby (for testing)
                    if (onSimulateNearby != null) {
                        OutlinedButton(
                            onClick = { onSimulateNearby(memory.id) },
                            shape = RoundedCornerShape(10.dp),
                            border = BorderStroke(1.dp, AmberWarning.copy(alpha = 0.5f)),
                            colors = ButtonDefaults.outlinedButtonColors(
                                containerColor = AmberLight.copy(alpha = 0.3f),
                                contentColor = AmberWarning
                            )
                        ) {
                            Text("⚡ Simulate Nearby", fontWeight = FontWeight.Medium)
                        }
                    }
                }
            }
        }
    }
}
