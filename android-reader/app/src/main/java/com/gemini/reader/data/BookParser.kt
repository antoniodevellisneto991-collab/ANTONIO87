package com.gemini.reader.data

import android.content.Context
import android.net.Uri
import java.io.BufferedReader
import java.io.InputStreamReader

/** Parsed book with pages of text. */
data class Book(
    val filename: String,
    val pages: List<String>,
    val totalChars: Int,
)

private const val CHARS_PER_PAGE = 3000

/** Read a .txt URI and split it into pages by paragraph. */
fun parseTxt(context: Context, uri: Uri, filename: String): Book {
    val text = context.contentResolver.openInputStream(uri)?.use { stream ->
        BufferedReader(InputStreamReader(stream, Charsets.UTF_8)).readText()
    }?.trim() ?: ""

    if (text.isEmpty()) return Book(filename, emptyList(), 0)

    val pages = mutableListOf<String>()
    val paragraphs = text.split("\n\n")
    val current = StringBuilder()

    for (para in paragraphs) {
        val trimmed = para.trim()
        if (trimmed.isEmpty()) continue

        if (current.length + trimmed.length + 2 > CHARS_PER_PAGE && current.isNotEmpty()) {
            pages.add(current.toString().trim())
            current.clear()
            current.append(trimmed)
        } else {
            if (current.isNotEmpty()) current.append("\n\n")
            current.append(trimmed)
        }
    }
    if (current.isNotBlank()) pages.add(current.toString().trim())

    // Fallback: if no paragraph breaks, split by char count
    if (pages.isEmpty() && text.isNotEmpty()) {
        var i = 0
        while (i < text.length) {
            pages.add(text.substring(i, minOf(i + CHARS_PER_PAGE, text.length)))
            i += CHARS_PER_PAGE
        }
    }

    return Book(filename, pages, text.length)
}

/**
 * Split text into chunks of at most [maxBytes] UTF-8 bytes,
 * breaking at paragraph or sentence boundaries when possible.
 * Gemini TTS limit: 4000 bytes per text field.
 */
fun splitTextIntoChunks(text: String, maxBytes: Int = 3800): List<String> {
    if (text.toByteArray(Charsets.UTF_8).size <= maxBytes) return listOf(text)

    val chunks = mutableListOf<String>()
    val paragraphs = text.split("\n\n")
    val current = StringBuilder()

    for (para in paragraphs) {
        val candidate = if (current.isEmpty()) para else "${current}\n\n${para}"
        if (candidate.toByteArray(Charsets.UTF_8).size > maxBytes) {
            if (current.isNotEmpty()) {
                chunks.add(current.toString())
                current.clear()
            }
            // If single paragraph exceeds limit, split by sentences
            if (para.toByteArray(Charsets.UTF_8).size > maxBytes) {
                val sentences = para.split(Regex("(?<=[.!?])\\s+"))
                for (sentence in sentences) {
                    val sentCandidate = if (current.isEmpty()) sentence else "${current} ${sentence}"
                    if (sentCandidate.toByteArray(Charsets.UTF_8).size > maxBytes) {
                        if (current.isNotEmpty()) chunks.add(current.toString())
                        current.clear()
                        current.append(sentence)
                    } else {
                        current.clear()
                        current.append(sentCandidate)
                    }
                }
            } else {
                current.append(para)
            }
        } else {
            current.clear()
            current.append(candidate)
        }
    }
    if (current.isNotEmpty()) chunks.add(current.toString())

    return chunks
}
