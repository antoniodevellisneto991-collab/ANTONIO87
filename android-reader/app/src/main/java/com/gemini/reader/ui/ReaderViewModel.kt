package com.gemini.reader.ui

import android.app.Application
import android.media.MediaPlayer
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.gemini.reader.data.*
import com.gemini.reader.tts.CloudTtsService
import com.gemini.reader.tts.TtsException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.io.File
import java.io.FileOutputStream

data class ReaderState(
    val book: Book? = null,
    val currentPage: Int = 0,
    val isLoading: Boolean = false,
    val isSynthesizing: Boolean = false,
    val isPlaying: Boolean = false,
    val autoMode: Boolean = false,
    val error: String? = null,
    // TTS settings
    val selectedModel: TtsModel = TtsModel.PRO,
    val selectedVoice: Voice = ALL_VOICES.first { it.name == "Kore" },
    val selectedStyle: StylePreset = STYLE_PRESETS.first(),
    val selectedLanguage: Language = LANGUAGES.first(),
    // Auth
    val accessToken: String = "",
    val isAuthenticated: Boolean = false,
)

class ReaderViewModel(app: Application) : AndroidViewModel(app) {

    private val _state = MutableStateFlow(ReaderState())
    val state = _state.asStateFlow()

    private var mediaPlayer: MediaPlayer? = null
    private var ttsService: CloudTtsService? = null

    fun setAccessToken(token: String) {
        ttsService = CloudTtsService(token)
        _state.update { it.copy(accessToken = token, isAuthenticated = true) }
    }

    fun openBook(uri: Uri, filename: String) {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            try {
                val book = parseTxt(getApplication(), uri, filename)
                if (book.pages.isEmpty()) {
                    _state.update { it.copy(isLoading = false, error = "Arquivo vazio") }
                    return@launch
                }
                _state.update { it.copy(book = book, currentPage = 0, isLoading = false) }
            } catch (e: Exception) {
                _state.update { it.copy(isLoading = false, error = "Erro ao ler arquivo: ${e.message}") }
            }
        }
    }

    fun goToPage(page: Int) {
        val book = _state.value.book ?: return
        if (page in book.pages.indices) {
            stopAudio()
            _state.update { it.copy(currentPage = page) }
        }
    }

    fun nextPage() = goToPage(_state.value.currentPage + 1)
    fun prevPage() = goToPage(_state.value.currentPage - 1)

    fun closeBook() {
        stopAudio()
        _state.update { it.copy(book = null, currentPage = 0, autoMode = false) }
    }

    // --- TTS settings ---

    fun setModel(model: TtsModel) = _state.update { it.copy(selectedModel = model) }
    fun setVoice(voice: Voice) = _state.update { it.copy(selectedVoice = voice) }
    fun setStyle(style: StylePreset) = _state.update { it.copy(selectedStyle = style) }
    fun setLanguage(lang: Language) = _state.update { it.copy(selectedLanguage = lang) }
    fun toggleAutoMode() = _state.update { it.copy(autoMode = !it.autoMode) }

    // --- Audio ---

    fun speakCurrentPage() {
        if (_state.value.isPlaying) {
            stopAudio()
            return
        }

        val service = ttsService
        if (service == null) {
            _state.update { it.copy(error = "Configure o Access Token primeiro") }
            return
        }

        val book = _state.value.book ?: return
        val text = book.pages[_state.value.currentPage]
        if (text.isBlank()) return

        val s = _state.value

        viewModelScope.launch {
            _state.update { it.copy(isSynthesizing = true, error = null) }
            try {
                val audioBytes = service.synthesizePage(
                    text = text,
                    prompt = s.selectedStyle.prompt,
                    voiceName = s.selectedVoice.name,
                    languageCode = s.selectedLanguage.code,
                    model = s.selectedModel,
                )
                playAudio(audioBytes)
                _state.update { it.copy(isSynthesizing = false, isPlaying = true) }
            } catch (e: TtsException) {
                _state.update { it.copy(isSynthesizing = false, error = e.message) }
            } catch (e: Exception) {
                _state.update { it.copy(isSynthesizing = false, error = "Erro: ${e.message}") }
            }
        }
    }

    private fun playAudio(audioBytes: ByteArray) {
        stopAudio()

        val tempFile = File.createTempFile("tts_", ".mp3", getApplication<Application>().cacheDir)
        FileOutputStream(tempFile).use { it.write(audioBytes) }

        mediaPlayer = MediaPlayer().apply {
            setDataSource(tempFile.absolutePath)
            prepare()
            setOnCompletionListener { onPlaybackComplete() }
            start()
        }
    }

    private fun onPlaybackComplete() {
        _state.update { it.copy(isPlaying = false) }

        if (_state.value.autoMode) {
            val book = _state.value.book ?: return
            if (_state.value.currentPage < book.pages.size - 1) {
                _state.update { it.copy(currentPage = it.currentPage + 1) }
                speakCurrentPage()
            } else {
                _state.update { it.copy(autoMode = false) }
            }
        }
    }

    fun stopAudio() {
        mediaPlayer?.apply {
            if (isPlaying) stop()
            release()
        }
        mediaPlayer = null
        _state.update { it.copy(isPlaying = false, isSynthesizing = false) }
    }

    fun clearError() = _state.update { it.copy(error = null) }

    override fun onCleared() {
        super.onCleared()
        mediaPlayer?.release()
    }
}
