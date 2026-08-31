package com.example.echo.data

import kotlinx.coroutines.delay
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.Response

/** Result of a /capture call. */
sealed interface CaptureOutcome {
    /** Already saved before (§33) - jump straight to the existing card. */
    data class Duplicate(val memoryId: String?, val message: String?) : CaptureOutcome
    /** Accepted; processing runs in the background - poll [jobId]. */
    data class Queued(val jobId: String) : CaptureOutcome
    data class Error(val message: String, val hint: String? = null) : CaptureOutcome
}

/** Terminal result of polling a job. */
sealed interface JobResult {
    data class Completed(val memoryId: String) : JobResult
    data class Failed(val message: String) : JobResult
}

/**
 * Thin async wrapper over [EchoApi]. Turns HTTP responses into sealed outcomes
 * and reads the backend's single error envelope (§41) so the UI never sees a
 * raw stack trace or status code.
 */
class EchoRepository(private val api: EchoApi = Network.api) {

    suspend fun capture(request: CaptureRequest): CaptureOutcome =
        try {
            val response = api.capture(request)
            val body = response.body()
            when {
                !response.isSuccessful || body == null ->
                    CaptureOutcome.Error(errorMessage(response), errorHint(response))
                body.duplicate ->
                    CaptureOutcome.Duplicate(body.memoryId, body.message)
                else ->
                    CaptureOutcome.Queued(body.jobId)
            }
        } catch (e: Exception) {
            CaptureOutcome.Error(networkMessage(e))
        }

    suspend fun captureImage(
        bytes: ByteArray,
        fileName: String,
        mimeType: String,
        source: String = "android_share",
        note: String? = null,
    ): CaptureOutcome =
        try {
            val media = (mimeType.ifBlank { "image/*" }).toMediaTypeOrNull()
            val filePart = MultipartBody.Part.createFormData(
                "file", fileName, bytes.toRequestBody(media)
            )
            val sourcePart = source.toRequestBody("text/plain".toMediaTypeOrNull())
            val notePart = note?.toRequestBody("text/plain".toMediaTypeOrNull())
            val response = api.captureImage(filePart, sourcePart, notePart)
            val body = response.body()
            when {
                !response.isSuccessful || body == null ->
                    CaptureOutcome.Error(errorMessage(response), errorHint(response))
                body.duplicate ->
                    CaptureOutcome.Duplicate(body.memoryId, body.message)
                else ->
                    CaptureOutcome.Queued(body.jobId)
            }
        } catch (e: Exception) {
            CaptureOutcome.Error(networkMessage(e))
        }

    /**
     * Polls the job until it reaches COMPLETED or FAILED. [onStage] receives the
     * server-authored stage copy each tick, rendered verbatim by the client.
     */
    suspend fun awaitJob(
        jobId: String,
        pollDelayMs: Long = 1_200,
        maxPolls: Int = 60,
        onStage: (String) -> Unit = {},
    ): JobResult {
        var lastMessage = "Understanding your save…"
        repeat(maxPolls) {
            val detail = try {
                api.job(jobId).body()
            } catch (e: Exception) {
                null
            }
            if (detail != null) {
                detail.stageMessage?.takeIf { it.isNotBlank() }?.let {
                    lastMessage = it
                    onStage(it)
                }
                when (detail.status) {
                    "COMPLETED" -> {
                        val memoryId = detail.memoryId
                        return if (memoryId != null) {
                            JobResult.Completed(memoryId)
                        } else {
                            JobResult.Failed("Saved, but the memory could not be loaded.")
                        }
                    }
                    "FAILED" ->
                        return JobResult.Failed(
                            detail.errorMessage ?: "Echo couldn't understand this one."
                        )
                }
            }
            delay(pollDelayMs)
        }
        return JobResult.Failed("$lastMessage (still working - check back shortly).")
    }

    suspend fun memory(memoryId: String): Result<MemoryDto> =
        callFor { api.memory(memoryId) }

    suspend fun overview(): Result<OverviewResponse> =
        callFor { api.overview() }

    suspend fun correct(memoryId: String, correction: MemoryCorrection): Result<MemoryDto> =
        callFor { api.correct(memoryId, correction) }

    /** The resurfacing feed the poller reads; defaults to freshly-SENT notices. */
    suspend fun notifications(status: String = "SENT"): Result<NotificationPage> =
        callFor { api.notifications(status = status) }

    /** Ack a notification. [action] "acted" (default) or "dismissed" (§22). */
    suspend fun ack(id: String, action: String = "acted"): Result<Unit> =
        callFor { api.ack(id, mapOf("action" to action)) }.map { }

    private suspend fun <T> callFor(block: suspend () -> Response<T>): Result<T> =
        try {
            val response = block()
            val body = response.body()
            if (response.isSuccessful && body != null) {
                Result.success(body)
            } else {
                Result.failure(EchoException(errorMessage(response), errorHint(response)))
            }
        } catch (e: Exception) {
            Result.failure(EchoException(networkMessage(e)))
        }

    private fun errorMessage(response: Response<*>): String =
        parseError(response)?.message
            ?: "Something went wrong (HTTP ${response.code()})."

    private fun errorHint(response: Response<*>): String? = parseError(response)?.hint

    private fun parseError(response: Response<*>): ErrorBody? =
        try {
            response.errorBody()?.string()?.takeIf { it.isNotBlank() }?.let { raw ->
                Network.json.decodeFromString(ErrorResponse.serializer(), raw).error
            }
        } catch (e: Exception) {
            null
        }

    private fun networkMessage(e: Exception): String =
        "Couldn't reach Echo. Check that the backend is running and reachable."
}

class EchoException(message: String, val hint: String? = null) : Exception(message)
