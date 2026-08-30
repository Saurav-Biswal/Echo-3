package com.example.echo.ui.share

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.echo.data.CaptureOutcome
import com.example.echo.data.CaptureRequest
import com.example.echo.data.EchoRepository
import com.example.echo.data.JobResult
import com.example.echo.data.MemoryDto
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed interface ShareUiState {
    data object Idle : ShareUiState
    data class Working(val message: String) : ShareUiState
    data class Ready(val memory: MemoryDto, val wasDuplicate: Boolean) : ShareUiState
    data class Failure(val message: String, val hint: String? = null) : ShareUiState
}

/** Drives SAVE -> UNDERSTAND -> show card for one shared item. */
class ShareViewModel(
    private val repo: EchoRepository = EchoRepository(),
) : ViewModel() {

    private val _state = MutableStateFlow<ShareUiState>(ShareUiState.Idle)
    val state: StateFlow<ShareUiState> = _state.asStateFlow()

    private var lastRun: (suspend () -> Unit)? = null

    fun submitText(content: String, inputType: String, note: String?) {
        val request = CaptureRequest(
            inputType = inputType,
            content = content,
            source = "android_share",
            note = note?.takeIf { it.isNotBlank() },
        )
        run { handleOutcome(repo.capture(request)) }
    }

    fun submitImage(bytes: ByteArray, fileName: String, mimeType: String, note: String?) {
        run {
            handleOutcome(
                repo.captureImage(
                    bytes = bytes,
                    fileName = fileName,
                    mimeType = mimeType,
                    note = note?.takeIf { it.isNotBlank() },
                )
            )
        }
    }

    fun retry() {
        lastRun?.let { block -> viewModelScope.launch { block() } }
    }

    private fun run(block: suspend () -> Unit) {
        lastRun = block
        _state.value = ShareUiState.Working("Saving to Echo…")
        viewModelScope.launch { block() }
    }

    private suspend fun handleOutcome(outcome: CaptureOutcome) {
        when (outcome) {
            is CaptureOutcome.Error ->
                _state.value = ShareUiState.Failure(outcome.message, outcome.hint)

            is CaptureOutcome.Duplicate -> {
                val id = outcome.memoryId
                if (id == null) {
                    _state.value = ShareUiState.Failure(
                        outcome.message ?: "You already saved this."
                    )
                } else {
                    loadMemory(id, wasDuplicate = true)
                }
            }

            is CaptureOutcome.Queued -> {
                _state.value = ShareUiState.Working("Understanding your save…")
                when (val result = repo.awaitJob(outcome.jobId) { stage ->
                    _state.value = ShareUiState.Working(stage)
                }) {
                    is JobResult.Completed -> loadMemory(result.memoryId, wasDuplicate = false)
                    is JobResult.Failed -> _state.value = ShareUiState.Failure(result.message)
                }
            }
        }
    }

    private suspend fun loadMemory(memoryId: String, wasDuplicate: Boolean) {
        repo.memory(memoryId)
            .onSuccess { _state.value = ShareUiState.Ready(it, wasDuplicate) }
            .onFailure {
                _state.value = ShareUiState.Failure(
                    it.message ?: "Saved, but the card could not be loaded."
                )
            }
    }
}
