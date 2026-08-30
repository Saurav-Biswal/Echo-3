package com.example.echo.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.echo.data.MemoryDto
import com.example.echo.ui.ActionLauncher
import com.example.echo.ui.Display
import com.example.echo.ui.theme.AcidGreen

@Composable
fun MemoryCard(memory: MemoryDto, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(4.dp), // Sharper, more industrial corners
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
        border = BorderStroke(1.dp, AcidGreen.copy(alpha = 0.3f))
    ) {
        Column(Modifier.padding(20.dp)) {
            // What: category + title
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                AssistChip(
                    onClick = {},
                    enabled = false,
                    shape = RoundedCornerShape(0.dp),
                    colors = AssistChipDefaults.assistChipColors(
                        disabledLabelColor = AcidGreen,
                        disabledContainerColor = Color.Transparent
                    ),
                    border = BorderStroke(1.dp, AcidGreen),
                    label = {
                        Text(
                            "${Display.categoryEmoji(memory.category)} ${Display.categoryLabel(memory.category).uppercase()}",
                            style = MaterialTheme.typography.labelSmall
                        )
                    },
                )
                
                Text(
                    "INTENTION_DETECTED",
                    style = MaterialTheme.typography.labelSmall,
                    color = AcidGreen,
                    fontSize = 10.sp
                )
            }
            
            Spacer(Modifier.height(12.dp))
            Text(
                text = Display.cardTitle(memory).uppercase(),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                color = Color.White
            )
            memory.summary?.takeIf { it.isNotBlank() }?.let {
                Spacer(Modifier.height(8.dp))
                Text(
                    it, 
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color.LightGray
                )
            }

            // Why: the reason Echo exists
            Spacer(Modifier.height(20.dp))
            Text(
                "// WHY_YOU_SAVED_THIS",
                style = MaterialTheme.typography.labelSmall,
                color = AcidGreen,
            )
            Spacer(Modifier.height(6.dp))
            Text(
                memory.whySaved, 
                style = MaterialTheme.typography.bodyLarge,
                fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace
            )

            // When: the resurfacing line
            Spacer(Modifier.height(16.dp))
            Text(
                "// STATUS",
                style = MaterialTheme.typography.labelSmall,
                color = AcidGreen,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                Display.whenLine(memory.triggers).uppercase(), 
                style = MaterialTheme.typography.bodySmall,
                color = Color.Gray
            )

            // Action: ordered buttons
            val actions = Display.orderedActions(memory.actions)
            if (actions.isNotEmpty()) {
                Spacer(Modifier.height(24.dp))
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    actions.forEach { action ->
                        val enabled = Display.actionLink(action) != null
                        if (action.isPrimary) {
                            Button(
                                onClick = { ActionLauncher.launch(context, action) },
                                enabled = enabled,
                                shape = RoundedCornerShape(0.dp),
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = AcidGreen,
                                    contentColor = Color.Black
                                )
                            ) { Text(action.label.uppercase()) }
                        } else {
                            OutlinedButton(
                                onClick = { ActionLauncher.launch(context, action) },
                                enabled = enabled,
                                shape = RoundedCornerShape(0.dp),
                                border = BorderStroke(1.dp, Color.White),
                                colors = ButtonDefaults.outlinedButtonColors(
                                    contentColor = Color.White
                                )
                            ) { Text(action.label.uppercase()) }
                        }
                    }
                }
            }
        }
    }
}
