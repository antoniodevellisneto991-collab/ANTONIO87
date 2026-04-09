package com.bookreader.gemini

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.bookreader.gemini.databinding.ActivityMainBinding
import com.google.ai.client.generativeai.GenerativeModel
import com.google.ai.client.generativeai.type.content
import com.google.ai.client.generativeai.type.generationConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.BufferedReader
import java.io.InputStreamReader

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    private var pages: List<String> = emptyList()
    private var currentPage = 0
    private var fontSize = 18f
    private var isPlaying = false
    private var autoMode = false
    private var audioTrack: AudioTrack? = null
    private var ttsJob: Job? = null

    private val styles = mapOf(
        0 to "Leia como um narrador profissional de audiobook, com tom calmo, pausas naturais e boa dicção.",
        1 to "Leia de forma dramática e expressiva, variando o tom conforme as emoções do texto.",
        2 to "Leia de forma suave, tranquila e reconfortante, como uma história antes de dormir.",
        3 to "Leia com energia e entusiasmo, mantendo o ouvinte engajado.",
        4 to "Leia de forma neutra e clara, sem emoção exagerada.",
        5 to "Leia como um poeta, com cadência rítmica e entonação musical.",
    )

    private val filePickerLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let { loadFile(it) }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupListeners()
    }

    private fun setupListeners() {
        binding.btnSelectFile.setOnClickListener {
            filePickerLauncher.launch("text/plain")
        }

        binding.btnBack.setOnClickListener {
            stopAudio()
            autoMode = false
            pages = emptyList()
            binding.uploadSection.visibility = View.VISIBLE
            binding.readerSection.visibility = View.GONE
            binding.toolbar.subtitle = null
        }

        binding.btnPrev.setOnClickListener {
            if (currentPage > 0) renderPage(currentPage - 1)
        }

        binding.btnNext.setOnClickListener {
            if (currentPage < pages.size - 1) renderPage(currentPage + 1)
        }

        binding.btnFontDown.setOnClickListener {
            if (fontSize > 12f) {
                fontSize -= 2f
                binding.tvContent.textSize = fontSize
            }
        }

        binding.btnFontUp.setOnClickListener {
            if (fontSize < 32f) {
                fontSize += 2f
                binding.tvContent.textSize = fontSize
            }
        }

        binding.btnSpeak.setOnClickListener {
            if (isPlaying) {
                stopAudio()
            } else {
                speakCurrentPage()
            }
        }

        binding.btnAuto.setOnClickListener {
            autoMode = !autoMode
            binding.btnAuto.isChecked = autoMode
            if (autoMode && !isPlaying) {
                speakCurrentPage()
            }
        }
    }

    private fun loadFile(uri: Uri) {
        lifecycleScope.launch {
            try {
                val text = withContext(Dispatchers.IO) {
                    contentResolver.openInputStream(uri)?.use { stream ->
                        BufferedReader(InputStreamReader(stream, "UTF-8")).readText()
                    } ?: ""
                }

                if (text.isBlank()) {
                    Toast.makeText(this@MainActivity, "Arquivo vazio", Toast.LENGTH_SHORT).show()
                    return@launch
                }

                pages = splitIntoPages(text)
                currentPage = 0

                val fileName = uri.lastPathSegment ?: "livro.txt"
                binding.toolbar.subtitle = fileName
                binding.tvFileName.text = fileName

                binding.uploadSection.visibility = View.GONE
                binding.readerSection.visibility = View.VISIBLE

                renderPage(0)

            } catch (e: Exception) {
                Toast.makeText(this@MainActivity, "Erro ao abrir: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun splitIntoPages(text: String, charsPerPage: Int = 3000): List<String> {
        val paragraphs = text.trim().split("\n\n")
        val result = mutableListOf<String>()
        var current = StringBuilder()

        for (para in paragraphs) {
            val trimmed = para.trim()
            if (trimmed.isEmpty()) continue

            if (current.length + trimmed.length + 2 > charsPerPage && current.isNotEmpty()) {
                result.add(current.toString().trim())
                current = StringBuilder(trimmed)
            } else {
                if (current.isNotEmpty()) current.append("\n\n")
                current.append(trimmed)
            }
        }

        if (current.isNotEmpty()) {
            result.add(current.toString().trim())
        }

        if (result.isEmpty() && text.isNotBlank()) {
            for (i in text.indices step charsPerPage) {
                result.add(text.substring(i, minOf(i + charsPerPage, text.length)))
            }
        }

        return result
    }

    private fun renderPage(index: Int) {
        if (index < 0 || index >= pages.size) return
        currentPage = index
        binding.tvContent.text = pages[index]
        binding.tvPageInfo.text = getString(R.string.page_format, index + 1, pages.size)
        binding.scrollView.scrollTo(0, 0)
        stopAudio()
    }

    private fun speakCurrentPage() {
        if (pages.isEmpty()) return
        val text = pages[currentPage]
        if (text.isBlank()) {
            Toast.makeText(this, "Página vazia", Toast.LENGTH_SHORT).show()
            return
        }

        isPlaying = true
        binding.btnSpeak.text = getString(R.string.generating)
        binding.btnSpeak.isEnabled = false

        val styleIndex = binding.spinnerStyle.selectedItemPosition
        val styleInstruction = styles[styleIndex] ?: styles[0]!!

        ttsJob = lifecycleScope.launch {
            try {
                val audioData = withContext(Dispatchers.IO) {
                    generateSpeech(text, styleInstruction)
                }

                if (audioData != null && isPlaying) {
                    binding.btnSpeak.text = getString(R.string.stop)
                    binding.btnSpeak.isEnabled = true
                    binding.audioProgress.visibility = View.VISIBLE

                    withContext(Dispatchers.IO) {
                        playAudio(audioData)
                    }

                    // Audio finished
                    withContext(Dispatchers.Main) {
                        onAudioFinished()
                    }
                } else {
                    withContext(Dispatchers.Main) {
                        stopAudio()
                        Toast.makeText(this@MainActivity, "Erro ao gerar áudio", Toast.LENGTH_SHORT).show()
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    stopAudio()
                    Toast.makeText(this@MainActivity, "Erro: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private suspend fun generateSpeech(text: String, styleInstruction: String): ByteArray? {
        val model = GenerativeModel(
            modelName = "gemini-2.5-flash-preview-tts",
            apiKey = BuildConfig.GEMINI_API_KEY,
            generationConfig = generationConfig {
                responseMimeType = "audio/pcm"
            },
            systemInstruction = content { text(styleInstruction + " Use o idioma Português (Brasil).") }
        )

        val response = model.generateContent(text)

        // Extract audio bytes from response
        response.candidates?.firstOrNull()?.content?.parts?.forEach { part ->
            val blob = part.inlineData
            if (blob != null) {
                return blob.data
            }
        }

        return null
    }

    private fun playAudio(audioData: ByteArray) {
        val sampleRate = 24000
        val bufferSize = AudioTrack.getMinBufferSize(
            sampleRate,
            AudioFormat.CHANNEL_OUT_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        )

        audioTrack = AudioTrack.Builder()
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build()
            )
            .setAudioFormat(
                AudioFormat.Builder()
                    .setSampleRate(sampleRate)
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                    .build()
            )
            .setBufferSizeInBytes(maxOf(bufferSize, audioData.size))
            .setTransferMode(AudioTrack.MODE_STATIC)
            .build()

        audioTrack?.write(audioData, 0, audioData.size)
        audioTrack?.play()

        // Wait for playback to finish
        val durationMs = (audioData.size.toLong() * 1000) / (sampleRate * 2)
        Thread.sleep(durationMs)

        audioTrack?.stop()
        audioTrack?.release()
        audioTrack = null
    }

    private fun onAudioFinished() {
        stopAudio()
        if (autoMode && currentPage < pages.size - 1) {
            renderPage(currentPage + 1)
            binding.root.postDelayed({ speakCurrentPage() }, 500)
        } else if (autoMode) {
            autoMode = false
            binding.btnAuto.isChecked = false
        }
    }

    private fun stopAudio() {
        isPlaying = false
        ttsJob?.cancel()
        ttsJob = null
        audioTrack?.stop()
        audioTrack?.release()
        audioTrack = null
        binding.btnSpeak.text = getString(R.string.listen)
        binding.btnSpeak.isEnabled = true
        binding.audioProgress.visibility = View.GONE
    }

    override fun onDestroy() {
        super.onDestroy()
        stopAudio()
    }
}
