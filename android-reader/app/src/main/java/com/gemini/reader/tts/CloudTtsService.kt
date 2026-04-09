package com.gemini.reader.tts

import com.gemini.reader.data.TtsModel
import com.gemini.reader.data.splitTextIntoChunks
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream
import java.util.concurrent.TimeUnit

/**
 * Calls the Google Cloud Text-to-Speech REST API with Gemini TTS models.
 *
 * Auth: uses the access token from `gcloud auth print-access-token`
 * or a service account key set via GOOGLE_APPLICATION_CREDENTIALS.
 */
class CloudTtsService(private val accessToken: String) {

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .build()

    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    /**
     * Synthesize a full page of text, automatically chunking if it exceeds
     * the 4000-byte API limit and concatenating the resulting audio.
     */
    suspend fun synthesizePage(
        text: String,
        prompt: String,
        voiceName: String = "Kore",
        languageCode: String = "pt-BR",
        model: TtsModel = TtsModel.PRO,
        audioEncoding: String = "MP3",
    ): ByteArray = withContext(Dispatchers.IO) {
        val chunks = splitTextIntoChunks(text)

        if (chunks.size == 1) {
            return@withContext synthesizeChunk(chunks[0], prompt, voiceName, languageCode, model, audioEncoding)
        }

        // Multiple chunks: synthesize each and concatenate
        val output = ByteArrayOutputStream()
        for (chunk in chunks) {
            val audio = synthesizeChunk(chunk, prompt, voiceName, languageCode, model, audioEncoding)
            output.write(audio)
        }
        output.toByteArray()
    }

    /**
     * Synthesize a single chunk of text (must be <= 4000 bytes).
     */
    private fun synthesizeChunk(
        text: String,
        prompt: String,
        voiceName: String,
        languageCode: String,
        model: TtsModel,
        audioEncoding: String,
    ): ByteArray {
        val body = buildJsonObject {
            put("input", buildJsonObject {
                put("text", text)
                put("prompt", prompt)
            })
            put("voice", buildJsonObject {
                put("languageCode", languageCode)
                put("name", voiceName)
                put("modelName", model.id)
            })
            put("audioConfig", buildJsonObject {
                put("audioEncoding", audioEncoding)
                put("sampleRateHertz", 24000)
            })
        }.toString()

        val request = Request.Builder()
            .url("https://texttospeech.googleapis.com/v1beta1/text:synthesize")
            .addHeader("Authorization", "Bearer $accessToken")
            .addHeader("Content-Type", "application/json")
            .post(body.toRequestBody(jsonMediaType))
            .build()

        val response = client.newCall(request).execute()
        val responseBody = response.body?.string()
            ?: throw TtsException("Empty response from TTS API")

        if (!response.isSuccessful) {
            throw TtsException("TTS API error ${response.code}: $responseBody")
        }

        val json = Json.parseToJsonElement(responseBody).jsonObject
        val audioContent = json["audioContent"]?.jsonPrimitive?.content
            ?: throw TtsException("No audioContent in response")

        return android.util.Base64.decode(audioContent, android.util.Base64.DEFAULT)
    }

    /**
     * Synthesize multi-speaker dialog.
     * Text format: "Speaker1: Hello!\nSpeaker2: Hi there!"
     */
    suspend fun synthesizeMultiSpeaker(
        text: String,
        prompt: String,
        speakers: List<Pair<String, String>>, // alias to voiceName
        languageCode: String = "pt-BR",
        model: TtsModel = TtsModel.PRO,
    ): ByteArray = withContext(Dispatchers.IO) {
        val body = buildJsonObject {
            put("input", buildJsonObject {
                put("text", text)
                put("prompt", prompt)
            })
            put("voice", buildJsonObject {
                put("languageCode", languageCode)
                put("modelName", model.id)
                put("multiSpeakerVoiceConfig", buildJsonObject {
                    put("speakerVoiceConfigs", buildJsonArray {
                        for ((alias, voice) in speakers) {
                            add(buildJsonObject {
                                put("speakerAlias", alias)
                                put("speakerId", voice)
                            })
                        }
                    })
                })
            })
            put("audioConfig", buildJsonObject {
                put("audioEncoding", "MP3")
                put("sampleRateHertz", 24000)
            })
        }.toString()

        val request = Request.Builder()
            .url("https://texttospeech.googleapis.com/v1beta1/text:synthesize")
            .addHeader("Authorization", "Bearer $accessToken")
            .addHeader("Content-Type", "application/json")
            .post(body.toRequestBody(jsonMediaType))
            .build()

        val response = client.newCall(request).execute()
        val responseBody = response.body?.string()
            ?: throw TtsException("Empty response from TTS API")

        if (!response.isSuccessful) {
            throw TtsException("TTS API error ${response.code}: $responseBody")
        }

        val json = Json.parseToJsonElement(responseBody).jsonObject
        val audioContent = json["audioContent"]?.jsonPrimitive?.content
            ?: throw TtsException("No audioContent in response")

        android.util.Base64.decode(audioContent, android.util.Base64.DEFAULT)
    }
}

class TtsException(message: String) : Exception(message)
