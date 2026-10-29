package ke.stratosmanager.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Stratos brand: deep-space navy + electric blue, saffron accent (Kenya sun).
private val LightScheme = lightColorScheme(
    primary = Color(0xFF1B4DFF),
    onPrimary = Color.White,
    secondary = Color(0xFFFFB300),
    background = Color(0xFFF6F8FF),
    surface = Color.White,
)
private val DarkScheme = darkColorScheme(
    primary = Color(0xFF7E9CFF),
    onPrimary = Color(0xFF0B1B3A),
    secondary = Color(0xFFFFD54F),
    background = Color(0xFF0B1220),
    surface = Color(0xFF121A2B),
)

@Composable
fun StratosTheme(darkTheme: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkScheme else LightScheme,
        content = content,
    )
}
