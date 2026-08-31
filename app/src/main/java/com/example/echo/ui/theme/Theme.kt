package com.example.echo.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightEchoColorScheme = lightColorScheme(
    primary = MintGreen,
    onPrimary = PureWhite,
    primaryContainer = MintGreenLight,
    onPrimaryContainer = ForestGreen,
    secondary = MintGreenDark,
    onSecondary = PureWhite,
    background = OffWhiteBackground,
    onBackground = TextPrimary,
    surface = PureWhite,
    onSurface = TextPrimary,
    surfaceVariant = SlateSurface,
    onSurfaceVariant = TextSecondary,
    outline = BorderLight,
    error = CoralAlert,
    onError = PureWhite,
    errorContainer = CoralLight,
    onErrorContainer = CoralAlert,
)

@Composable
fun EchoTheme(
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = LightEchoColorScheme,
        typography = Typography,
        content = content
    )
}

