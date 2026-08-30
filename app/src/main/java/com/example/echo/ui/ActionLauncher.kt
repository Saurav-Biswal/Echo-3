package com.example.echo.ui

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import com.example.echo.data.ActionDto

/** Fires a memory action as an Android intent, with graceful fallbacks. */
object ActionLauncher {

    fun launch(context: Context, action: ActionDto) {
        val primary = action.deepLink?.takeIf { it.isNotBlank() }
        val fallback = action.webLink?.takeIf { it.isNotBlank() }

        if (primary != null && tryView(context, primary)) return
        if (fallback != null && tryView(context, fallback)) return

        Toast.makeText(context, "Nothing to open for this action.", Toast.LENGTH_SHORT).show()
    }

    private fun tryView(context: Context, uri: String): Boolean =
        try {
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(uri)).apply {
                if (context !is android.app.Activity) addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
            true
        } catch (e: ActivityNotFoundException) {
            false
        } catch (e: Exception) {
            false
        }
}
