package com.example.echo.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.echo.data.CaptureOutcome
import com.example.echo.data.CaptureRequest
import com.example.echo.data.EchoRepository
import com.example.echo.data.JobResult
import com.example.echo.data.MemoryDto
import com.example.echo.data.OverviewResponse
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed interface HomeUiState {
    data object Loading : HomeUiState
    data class Loaded(val overview: OverviewResponse) : HomeUiState
    data class Error(val message: String) : HomeUiState
}

/** Dashboard: overview counts + recent memories, with an inline paste-to-save. */
class HomeViewModel(
    private val repo: EchoRepository = EchoRepository(),
) : ViewModel() {

    private val _state = MutableStateFlow<HomeUiState>(HomeUiState.Loading)
    val state: StateFlow<HomeUiState> = _state.asStateFlow()

    private val _capture = MutableStateFlow<String?>(null)
    /** Transient one-line status for the inline capture box; null when idle. */
    val captureStatus: StateFlow<String?> = _capture.asStateFlow()

    private val _focused = MutableStateFlow<MemoryDto?>(null)
    /** A memory to surface front-and-center (e.g. opened from a notification tap). */
    val focusedMemory: StateFlow<MemoryDto?> = _focused.asStateFlow()

    private val _simStatus = MutableStateFlow<String?>(null)
    /** Transient feedback for the Simulate Nearby action. */
    val simStatus: StateFlow<String?> = _simStatus.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            if (_state.value !is HomeUiState.Loaded) _state.value = HomeUiState.Loading
            repo.overview()
                .onSuccess { _state.value = HomeUiState.Loaded(it) }
                .onFailure { _state.value = HomeUiState.Error(it.message ?: "Couldn't load Echo.") }
        }
    }

    fun captureText(content: String, note: String?) {
        val trimmed = content.trim()
        if (trimmed.isEmpty()) return
        val looksLikeUrl = trimmed.none { it.isWhitespace() } &&
            (trimmed.startsWith("http://") || trimmed.startsWith("https://"))
        val request = CaptureRequest(
            inputType = if (looksLikeUrl) "url" else "text",
            content = trimmed,
            source = "dashboard",
            note = note?.takeIf { it.isNotBlank() },
        )
        viewModelScope.launch {
            _capture.value = "Saving…"
            when (val outcome = repo.capture(request)) {
                is CaptureOutcome.Error -> _capture.value = outcome.message
                is CaptureOutcome.Duplicate -> {
                    _capture.value = "Already saved ✓"
                    refresh()
                }
                is CaptureOutcome.Queued -> {
                    when (val result = repo.awaitJob(outcome.jobId) { _capture.value = it }) {
                        is JobResult.Completed -> {
                            _capture.value = "Saved ✓"
                            refresh()
                        }
                        is JobResult.Failed -> _capture.value = result.message
                    }
                }
            }
        }
    }

    fun clearCaptureStatus() {
        _capture.value = null
    }

    /** Simulate a geofence ENTER for a specific memory (demo action, §45). */
    fun simulateNearby(memoryId: String) {
        viewModelScope.launch {
            _simStatus.value = "⚡ Resurfacing…"
            repo.simulateNearby(memoryId)
                .onSuccess { resp ->
                    _simStatus.value = if (resp.fired > 0) {
                        "📍 Memory resurfaced! Notification incoming…"
                    } else {
                        resp.message ?: "No pending trigger to fire."
                    }
                }
                .onFailure { e ->
                    _simStatus.value = "❌ ${e.message ?: "Simulate failed."}"
                }
            // Auto-clear after a few seconds
            kotlinx.coroutines.delay(4000)
            _simStatus.value = null
        }
    }

    /** Load a memory and surface it (called when a notification is tapped). */
    fun openMemory(memoryId: String) {
        viewModelScope.launch {
            repo.memory(memoryId).onSuccess { _focused.value = it }
        }
    }

    fun dismissFocused() {
        _focused.value = null
    }

    /** Delete a memory and refresh the dashboard. */
    fun deleteMemory(memoryId: String) {
        viewModelScope.launch {
            repo.deleteMemory(memoryId).onSuccess {
                if (_focused.value?.id == memoryId) {
                    _focused.value = null
                }
                refresh()
            }
        }
    }

    /** Mark a memory as completed and refresh the dashboard. */
    fun completeMemory(memoryId: String) {
        viewModelScope.launch {
            repo.completeMemory(memoryId).onSuccess {
                if (_focused.value?.id == memoryId) {
                    _focused.value = it
                }
                refresh()
            }
        }
    }
}

