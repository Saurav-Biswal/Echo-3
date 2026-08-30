package com.example.echo.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val DoomsdayColorScheme = darkColorScheme(
    primary = AcidGreen,
    secondary = WarningOrange,
    tertiary = AlertRed,
    background = BaseBlack,
    surface = CharcoalSurface,
    onPrimary = BaseBlack,
    onSecondary = BaseBlack,
    onTertiary = OffWhite,
    onBackground = OffWhite,
    onSurface = OffWhite,
    surfaceVariant = DarkGrey,
    onSurfaceVariant = OffWhite
)

@Composable
fun EchoTheme(
    content: @Composable () -> Unit
) {
    // Forcing dark theme for the Doomsday Engine experience
    MaterialTheme(
        colorScheme = DoomsdayColorScheme,
        typography = Typography,
        content = content
    )
}
