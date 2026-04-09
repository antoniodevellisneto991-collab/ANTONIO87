package com.gemini.reader.ui

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.NavigateBefore
import androidx.compose.material.icons.automirrored.filled.NavigateNext
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.gemini.reader.data.*

@Composable
fun ReaderApp(vm: ReaderViewModel = viewModel()) {
    val state by vm.state.collectAsState()

    GeminiReaderTheme {
        Surface(modifier = Modifier.fillMaxSize()) {
            if (state.book == null) {
                UploadScreen(state, vm)
            } else {
                ReaderScreen(state, vm)
            }
        }

        // Error snackbar
        state.error?.let { error ->
            AlertDialog(
                onDismissRequest = { vm.clearError() },
                title = { Text("Erro") },
                text = { Text(error) },
                confirmButton = {
                    TextButton(onClick = { vm.clearError() }) { Text("OK") }
                }
            )
        }
    }
}

// --- Upload Screen ---

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun UploadScreen(state: ReaderState, vm: ReaderViewModel) {
    var tokenInput by remember { mutableStateOf(state.accessToken) }

    val filePicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri: Uri? ->
        uri?.let { vm.openBook(it, "livro.txt") }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp)
            .verticalScroll(rememberScrollState()),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Icon(
            Icons.Default.MenuBook,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(64.dp),
        )
        Spacer(Modifier.height(16.dp))
        Text(
            "Gemini Book Reader",
            style = MaterialTheme.typography.headlineMedium,
        )
        Text(
            "Pro + Flash TTS \u2014 30 vozes neurais",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        Spacer(Modifier.height(32.dp))

        // Access Token
        OutlinedTextField(
            value = tokenInput,
            onValueChange = { tokenInput = it },
            label = { Text("Access Token (gcloud auth print-access-token)") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        Spacer(Modifier.height(8.dp))
        Button(
            onClick = { vm.setAccessToken(tokenInput.trim()) },
            enabled = tokenInput.isNotBlank(),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(if (state.isAuthenticated) "Token Configurado" else "Salvar Token")
        }

        Spacer(Modifier.height(24.dp))

        // File picker
        OutlinedButton(
            onClick = { filePicker.launch(arrayOf("text/plain")) },
            enabled = state.isAuthenticated && !state.isLoading,
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp),
        ) {
            if (state.isLoading) {
                CircularProgressIndicator(modifier = Modifier.size(24.dp))
                Spacer(Modifier.width(8.dp))
                Text("Carregando...")
            } else {
                Icon(Icons.Default.UploadFile, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("Escolher arquivo .txt")
            }
        }

        Spacer(Modifier.height(16.dp))
        Text(
            "1) No Cloud Shell: gcloud auth print-access-token\n2) Cole o token acima\n3) Escolha o arquivo .txt",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
        )
    }
}

// --- Reader Screen ---

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ReaderScreen(state: ReaderState, vm: ReaderViewModel) {
    val book = state.book ?: return
    var showSettings by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        book.filename,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        style = MaterialTheme.typography.titleSmall,
                    )
                },
                navigationIcon = {
                    IconButton(onClick = { vm.closeBook() }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Voltar")
                    }
                },
                actions = {
                    Text(
                        "${state.currentPage + 1}/${book.pages.size}",
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(end = 8.dp),
                    )
                    IconButton(onClick = { showSettings = !showSettings }) {
                        Icon(Icons.Default.Settings, "Configuracoes")
                    }
                },
            )
        },
        bottomBar = {
            AudioControlBar(state, vm)
        },
    ) { padding ->
        Column(modifier = Modifier.padding(padding).fillMaxSize()) {
            // Settings panel
            AnimatedVisibility(visible = showSettings) {
                SettingsPanel(state, vm)
            }

            // Page navigation
            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(
                    onClick = { vm.prevPage() },
                    enabled = state.currentPage > 0,
                ) {
                    Icon(Icons.AutoMirrored.Filled.NavigateBefore, "Anterior")
                }
                Text(
                    "Pagina ${state.currentPage + 1} de ${book.pages.size}",
                    style = MaterialTheme.typography.bodySmall,
                )
                IconButton(
                    onClick = { vm.nextPage() },
                    enabled = state.currentPage < book.pages.size - 1,
                ) {
                    Icon(Icons.AutoMirrored.Filled.NavigateNext, "Proxima")
                }
            }

            // Text content
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp)
                    .verticalScroll(rememberScrollState()),
            ) {
                Text(
                    text = book.pages[state.currentPage],
                    fontFamily = FontFamily.Serif,
                    fontSize = 17.sp,
                    lineHeight = 30.sp,
                    modifier = Modifier.padding(vertical = 16.dp),
                )
            }
        }
    }
}

// --- Settings Panel ---

@Composable
private fun SettingsPanel(state: ReaderState, vm: ReaderViewModel) {
    var modelExpanded by remember { mutableStateOf(false) }
    var voiceExpanded by remember { mutableStateOf(false) }
    var styleExpanded by remember { mutableStateOf(false) }
    var langExpanded by remember { mutableStateOf(false) }

    Surface(
        tonalElevation = 2.dp,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text("Configuracoes TTS", style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.height(8.dp))

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                // Model
                DropdownSelector(
                    label = "Modelo",
                    selected = state.selectedModel.label,
                    expanded = modelExpanded,
                    onToggle = { modelExpanded = !modelExpanded },
                    onDismiss = { modelExpanded = false },
                    modifier = Modifier.weight(1f),
                ) {
                    TtsModel.entries.forEach { model ->
                        DropdownMenuItem(
                            text = { Text(model.label, fontSize = 13.sp) },
                            onClick = { vm.setModel(model); modelExpanded = false },
                        )
                    }
                }

                // Style
                DropdownSelector(
                    label = "Estilo",
                    selected = state.selectedStyle.label,
                    expanded = styleExpanded,
                    onToggle = { styleExpanded = !styleExpanded },
                    onDismiss = { styleExpanded = false },
                    modifier = Modifier.weight(1f),
                ) {
                    STYLE_PRESETS.forEach { style ->
                        DropdownMenuItem(
                            text = { Text(style.label, fontSize = 13.sp) },
                            onClick = { vm.setStyle(style); styleExpanded = false },
                        )
                    }
                }
            }

            Spacer(Modifier.height(8.dp))

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                // Voice
                DropdownSelector(
                    label = "Voz",
                    selected = "${state.selectedVoice.name} (${if (state.selectedVoice.gender == Gender.F) "F" else "M"})",
                    expanded = voiceExpanded,
                    onToggle = { voiceExpanded = !voiceExpanded },
                    onDismiss = { voiceExpanded = false },
                    modifier = Modifier.weight(1f),
                ) {
                    ALL_VOICES.forEach { voice ->
                        val gLabel = if (voice.gender == Gender.F) "F" else "M"
                        DropdownMenuItem(
                            text = { Text("${voice.name} ($gLabel)", fontSize = 13.sp) },
                            onClick = { vm.setVoice(voice); voiceExpanded = false },
                        )
                    }
                }

                // Language
                DropdownSelector(
                    label = "Idioma",
                    selected = state.selectedLanguage.label,
                    expanded = langExpanded,
                    onToggle = { langExpanded = !langExpanded },
                    onDismiss = { langExpanded = false },
                    modifier = Modifier.weight(1f),
                ) {
                    LANGUAGES.forEach { lang ->
                        DropdownMenuItem(
                            text = { Text(lang.label, fontSize = 13.sp) },
                            onClick = { vm.setLanguage(lang); langExpanded = false },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun DropdownSelector(
    label: String,
    selected: String,
    expanded: Boolean,
    onToggle: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
    content: @Composable ColumnScope.() -> Unit,
) {
    Box(modifier = modifier) {
        OutlinedButton(
            onClick = onToggle,
            modifier = Modifier.fillMaxWidth(),
            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 8.dp),
        ) {
            Column(horizontalAlignment = Alignment.Start, modifier = Modifier.weight(1f)) {
                Text(label, fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text(selected, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            Icon(Icons.Default.ArrowDropDown, null, modifier = Modifier.size(18.dp))
        }
        DropdownMenu(expanded = expanded, onDismissRequest = onDismiss, content = content)
    }
}

// --- Audio Control Bar ---

@Composable
private fun AudioControlBar(state: ReaderState, vm: ReaderViewModel) {
    Surface(
        tonalElevation = 3.dp,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // Speak button
            Button(
                onClick = { vm.speakCurrentPage() },
                enabled = !state.isSynthesizing,
                colors = if (state.isPlaying)
                    ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                else ButtonDefaults.buttonDefaults(),
                modifier = Modifier.weight(1f),
            ) {
                if (state.isSynthesizing) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(18.dp),
                        color = MaterialTheme.colorScheme.onPrimary,
                        strokeWidth = 2.dp,
                    )
                    Spacer(Modifier.width(8.dp))
                    Text("Gerando...")
                } else if (state.isPlaying) {
                    Icon(Icons.Default.Stop, null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(8.dp))
                    Text("Parar")
                } else {
                    Icon(Icons.Default.VolumeUp, null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(8.dp))
                    Text("Ouvir Pagina")
                }
            }

            Spacer(Modifier.width(12.dp))

            // Auto mode
            OutlinedButton(
                onClick = { vm.toggleAutoMode(); if (!state.autoMode && !state.isPlaying) vm.speakCurrentPage() },
                colors = if (state.autoMode)
                    ButtonDefaults.outlinedButtonColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
                else ButtonDefaults.outlinedButtonColors(),
            ) {
                Icon(Icons.Default.PlayArrow, null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(4.dp))
                Text("Auto")
            }
        }
    }
}

@Composable
private fun ButtonDefaults.buttonDefaults() = buttonColors()
