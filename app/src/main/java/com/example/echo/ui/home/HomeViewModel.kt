package com.example.echo.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.echo.data.CaptureOutcome
import com.example.echo.data.CaptureRequest
import com.example.echo.data.EchoRepository
import com.example.echo.data.JobResult
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
}
