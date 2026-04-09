package com.gemini.reader.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val Purple = Color(0xFF8B5CF6)
private val PurpleLight = Color(0xFFA78BFA)

private val LightColors = lightColorScheme(
    primary = Purple,
    onPrimary = Color.White,
    surface = Color(0xFFFDFCFA),
    onSurface = Color(0xFF1A1A1A),
    surfaceVariant = Color(0xFFF7F5F2),
    onSurfaceVariant = Color(0xFF555555),
    outline = Color(0xFFE6E3DE),
)

private val DarkColors = darkColorScheme(
    primary = PurpleLight,
    onPrimary = Color.White,
    surface = Color(0xFF0D0D0D),
    onSurface = Color(0xFFE8E4DF),
    surfaceVariant = Color(0xFF141414),
    onSurfaceVariant = Color(0xFFA0A0A0),
    outline = Color(0xFF2A2A2A),
)

@Composable
fun GeminiReaderTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        content = content,
    )
}
