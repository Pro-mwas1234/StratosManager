package ke.stratosmanager.app.ui

import androidx.compose.runtime.Composable
import ke.stratosmanager.app.ui.auth.LoginScreen

/**
 * Navigation graph (A3): login -> shell (dashboard + module tabs) -> module routes.
 * Routes mirror docs/API-CONTRACT.md screens: retail POS, invoices, restaurant,
 * hotel, property, manufacturing, billing upgrade sheet.
 */
@Composable
fun StratosNavHost() {
    // A3 wires NavHostController + auth-driven start destination.
    LoginScreen()
}
