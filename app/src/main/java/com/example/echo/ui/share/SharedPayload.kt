package com.example.echo.ui.share

import android.net.Uri

/** The content the user shared into Echo. */
sealed interface SharedPayload {
    data class Text(val content: String, val inputType: String) : SharedPayload
    data class Image(val uri: Uri, val fileName: String, val mimeType: String) : SharedPayload
}
