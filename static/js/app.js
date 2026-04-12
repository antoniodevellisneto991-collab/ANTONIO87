/**
 * Cloud Book Reader - Frontend Application
 * Leitor de livros EPUB com Google Cloud TTS
 */

(function () {
    "use strict";

    // --- State ---
    let bookData = null;
    let currentChapter = 0;
    let fontSize = 1.1;
    let isPlaying = false;
    let audioPlayer = document.getElementById("audio-player");

    // --- DOM Elements ---
    const uploadSection = document.getElementById("upload-section");
    const readerSection = document.getElementById("reader-section");
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const btnSelect = document.getElementById("btn-select");
    const uploadProgress = document.getElementById("upload-progress");
    const progressFill = document.getElementById("progress-fill");
    const uploadStatus = document.getElementById("upload-status");

    // TXT Split elements
    const dropZoneTxt = document.getElementById("drop-zone-txt");
    const fileInputTxt = document.getElementById("file-input-txt");
    const btnSelectTxt = document.getElementById("btn-select-txt");
    const chunkSizeInput = document.getElementById("chunk-size");
    const tabEpub = document.getElementById("tab-epub");
    const tabSplit = document.getElementById("tab-split");

    const sidebar = document.getElementById("sidebar");
    const toc = document.getElementById("toc");
    const bookCover = document.getElementById("book-cover");
    const metaTitle = document.getElementById("meta-title");
    const metaAuthor = document.getElementById("meta-author");

    const pageContent = document.getElementById("page-content");
    const chapterTitle = document.getElementById("chapter-title");
    const currentChapterEl = document.getElementById("current-chapter");
    const totalChaptersEl = document.getElementById("total-chapters");

    const btnBack = document.getElementById("btn-back");
    const btnPrev = document.getElementById("btn-prev");
    const btnNext = document.getElementById("btn-next");
    const btnTts = document.getElementById("btn-tts");
    const btnFontDecrease = document.getElementById("btn-font-decrease");
    const btnFontIncrease = document.getElementById("btn-font-increase");
    const btnToggleSidebar = document.getElementById("btn-toggle-sidebar");
    const btnTheme = document.getElementById("btn-theme");
    const ttsLanguage = document.getElementById("tts-language");

    // --- Tab Switching ---
    function switchTab(tab) {
        var panels = uploadSection.querySelectorAll(".upload-area");
        panels.forEach(function (p) { p.classList.add("hidden"); });
        tabEpub.classList.remove("active");
        tabSplit.classList.remove("active");

        if (tab === "epub") {
            dropZone.classList.remove("hidden");
            tabEpub.classList.add("active");
        } else {
            dropZoneTxt.classList.remove("hidden");
            tabSplit.classList.add("active");
        }
    }

    tabEpub.addEventListener("click", function () { switchTab("epub"); });
    tabSplit.addEventListener("click", function () { switchTab("split"); });

    // --- TXT Split Upload ---
    btnSelectTxt.addEventListener("click", function () {
        fileInputTxt.click();
    });

    dropZoneTxt.addEventListener("click", function (e) {
        if (e.target !== btnSelectTxt && !btnSelectTxt.contains(e.target)
            && e.target.tagName !== "INPUT" && e.target.tagName !== "LABEL") {
            fileInputTxt.click();
        }
    });

    dropZoneTxt.addEventListener("dragover", function (e) {
        e.preventDefault();
        dropZoneTxt.classList.add("dragover");
    });

    dropZoneTxt.addEventListener("dragleave", function () {
        dropZoneTxt.classList.remove("dragover");
    });

    dropZoneTxt.addEventListener("drop", function (e) {
        e.preventDefault();
        dropZoneTxt.classList.remove("dragover");
        var files = e.dataTransfer.files;
        if (files.length > 0) {
            handleTxtFile(files[0]);
        }
    });

    fileInputTxt.addEventListener("change", function () {
        if (fileInputTxt.files.length > 0) {
            handleTxtFile(fileInputTxt.files[0]);
        }
    });

    function handleTxtFile(file) {
        if (!file.name.toLowerCase().endsWith(".txt")) {
            alert("Por favor, selecione um arquivo TXT.");
            return;
        }

        if (file.size > 50 * 1024 * 1024) {
            alert("O arquivo excede o limite de 50MB.");
            return;
        }

        uploadTxtFile(file);
    }

    function uploadTxtFile(file) {
        dropZoneTxt.classList.add("hidden");
        uploadProgress.classList.remove("hidden");
        progressFill.style.width = "20%";
        uploadStatus.textContent = "Enviando e dividindo arquivo...";

        var formData = new FormData();
        formData.append("file", file);
        formData.append("chunk_size", chunkSizeInput.value || "5000");

        var xhr = new XMLHttpRequest();
        xhr.open("POST", "/split-txt", true);
        xhr.responseType = "blob";

        xhr.upload.addEventListener("progress", function (e) {
            if (e.lengthComputable) {
                var pct = Math.round((e.loaded / e.total) * 60) + 20;
                progressFill.style.width = pct + "%";
            }
        });

        xhr.addEventListener("load", function () {
            if (xhr.status === 200) {
                progressFill.style.width = "100%";
                uploadStatus.textContent = "Download pronto!";

                // Trigger download of the ZIP
                var blob = xhr.response;
                var url = URL.createObjectURL(blob);
                var a = document.createElement("a");
                var baseName = file.name.replace(/\.txt$/i, "");
                a.href = url;
                a.download = baseName + "_dividido.zip";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);

                setTimeout(resetTxtUpload, 1500);
            } else {
                // Read error from blob response
                var reader = new FileReader();
                reader.onload = function () {
                    try {
                        var err = JSON.parse(reader.result);
                        uploadStatus.textContent = "Erro: " + (err.error || "Falha no processamento");
                    } catch (_e) {
                        uploadStatus.textContent = "Erro no processamento.";
                    }
                };
                reader.readAsText(xhr.response);
                progressFill.style.width = "0%";
                setTimeout(resetTxtUpload, 2000);
            }
        });

        xhr.addEventListener("error", function () {
            uploadStatus.textContent = "Erro de conexão. Tente novamente.";
            setTimeout(resetTxtUpload, 2000);
        });

        xhr.send(formData);
    }

    function resetTxtUpload() {
        dropZoneTxt.classList.remove("hidden");
        uploadProgress.classList.add("hidden");
        progressFill.style.width = "0%";
        fileInputTxt.value = "";
    }

    // --- Theme ---
    function initTheme() {
        const saved = localStorage.getItem("theme");
        if (saved === "dark" || (!saved && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
            document.documentElement.setAttribute("data-theme", "dark");
            toggleThemeIcons(true);
        }
    }

    function toggleThemeIcons(isDark) {
        document.getElementById("icon-sun").classList.toggle("hidden", isDark);
        document.getElementById("icon-moon").classList.toggle("hidden", !isDark);
    }

    btnTheme.addEventListener("click", function () {
        const isDark = document.documentElement.getAttribute("data-theme") === "dark";
        if (isDark) {
            document.documentElement.removeAttribute("data-theme");
            localStorage.setItem("theme", "light");
            toggleThemeIcons(false);
        } else {
            document.documentElement.setAttribute("data-theme", "dark");
            localStorage.setItem("theme", "dark");
            toggleThemeIcons(true);
        }
    });

    initTheme();

    // --- File Upload ---
    btnSelect.addEventListener("click", function () {
        fileInput.click();
    });

    dropZone.addEventListener("click", function (e) {
        if (e.target !== btnSelect && !btnSelect.contains(e.target)) {
            fileInput.click();
        }
    });

    dropZone.addEventListener("dragover", function (e) {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", function () {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", function (e) {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        var files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });

    fileInput.addEventListener("change", function () {
        if (fileInput.files.length > 0) {
            handleFile(fileInput.files[0]);
        }
    });

    function handleFile(file) {
        if (!file.name.toLowerCase().endsWith(".epub")) {
            alert("Por favor, selecione um arquivo EPUB.");
            return;
        }

        if (file.size > 50 * 1024 * 1024) {
            alert("O arquivo excede o limite de 50MB.");
            return;
        }

        uploadFile(file);
    }

    function uploadFile(file) {
        dropZone.classList.add("hidden");
        uploadProgress.classList.remove("hidden");
        progressFill.style.width = "20%";
        uploadStatus.textContent = "Enviando arquivo...";

        var formData = new FormData();
        formData.append("file", file);

        var xhr = new XMLHttpRequest();
        xhr.open("POST", "/upload", true);

        xhr.upload.addEventListener("progress", function (e) {
            if (e.lengthComputable) {
                var pct = Math.round((e.loaded / e.total) * 60) + 20;
                progressFill.style.width = pct + "%";
            }
        });

        xhr.addEventListener("load", function () {
            if (xhr.status === 200) {
                progressFill.style.width = "90%";
                uploadStatus.textContent = "Processando livro...";

                var data = JSON.parse(xhr.responseText);
                progressFill.style.width = "100%";

                setTimeout(function () {
                    loadBook(data);
                }, 300);
            } else {
                var err = JSON.parse(xhr.responseText);
                uploadStatus.textContent = "Erro: " + (err.error || "Falha no upload");
                progressFill.style.width = "0%";
                setTimeout(resetUpload, 2000);
            }
        });

        xhr.addEventListener("error", function () {
            uploadStatus.textContent = "Erro de conexão. Tente novamente.";
            setTimeout(resetUpload, 2000);
        });

        xhr.send(formData);
    }

    function resetUpload() {
        dropZone.classList.remove("hidden");
        uploadProgress.classList.add("hidden");
        progressFill.style.width = "0%";
        fileInput.value = "";
    }

    // --- Book Loading ---
    function loadBook(data) {
        bookData = data;
        currentChapter = 0;

        // Set metadata
        var meta = data.metadata || {};
        metaTitle.textContent = meta.title || data.filename;
        metaAuthor.textContent = meta.author || "";
        document.title = (meta.title || "Livro") + " — Cloud Book Reader";

        // Cover
        if (meta.cover) {
            bookCover.innerHTML = '<img src="data:image/jpeg;base64,' + meta.cover + '" alt="Capa">';
        } else {
            bookCover.innerHTML = '<span class="cover-placeholder">📖</span>';
        }

        // Table of contents
        toc.innerHTML = "";
        data.chapters.forEach(function (ch, i) {
            var btn = document.createElement("button");
            btn.className = "toc-item";
            btn.textContent = ch.title;
            btn.addEventListener("click", function () {
                goToChapter(i);
            });
            toc.appendChild(btn);
        });

        totalChaptersEl.textContent = data.total_chapters;

        // Show reader
        uploadSection.classList.add("hidden");
        readerSection.classList.remove("hidden");

        // Auto-detect language for TTS
        if (meta.language) {
            var lang = meta.language.toLowerCase();
            var options = ttsLanguage.options;
            for (var j = 0; j < options.length; j++) {
                if (options[j].value.toLowerCase().startsWith(lang)) {
                    ttsLanguage.selectedIndex = j;
                    break;
                }
            }
        }

        renderChapter(0);
    }

    // --- Chapter Navigation ---
    function renderChapter(index) {
        if (!bookData || index < 0 || index >= bookData.chapters.length) return;

        currentChapter = index;
        var chapter = bookData.chapters[index];

        // Render HTML content
        pageContent.innerHTML = chapter.html || "<p>" + escapeHtml(chapter.text) + "</p>";
        chapterTitle.textContent = chapter.title;
        currentChapterEl.textContent = index + 1;

        // Update TOC active
        var items = toc.querySelectorAll(".toc-item");
        items.forEach(function (item, i) {
            item.classList.toggle("active", i === index);
        });

        // Scroll to top
        document.getElementById("reader-content").scrollTop = 0;

        // Stop any playing audio
        stopAudio();

        // Save position
        localStorage.setItem("lastChapter", index);
    }

    function goToChapter(index) {
        renderChapter(index);
        // Close sidebar on mobile
        if (window.innerWidth <= 768) {
            sidebar.classList.add("collapsed");
        }
    }

    btnPrev.addEventListener("click", function () {
        if (currentChapter > 0) renderChapter(currentChapter - 1);
    });

    btnNext.addEventListener("click", function () {
        if (bookData && currentChapter < bookData.chapters.length - 1) {
            renderChapter(currentChapter + 1);
        }
    });

    // Keyboard navigation
    document.addEventListener("keydown", function (e) {
        if (!bookData) return;
        if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;

        if (e.key === "ArrowLeft") {
            e.preventDefault();
            if (currentChapter > 0) renderChapter(currentChapter - 1);
        } else if (e.key === "ArrowRight") {
            e.preventDefault();
            if (currentChapter < bookData.chapters.length - 1) renderChapter(currentChapter + 1);
        }
    });

    // --- Font Size ---
    btnFontDecrease.addEventListener("click", function () {
        if (fontSize > 0.8) {
            fontSize -= 0.1;
            pageContent.style.fontSize = fontSize + "rem";
        }
    });

    btnFontIncrease.addEventListener("click", function () {
        if (fontSize < 2.0) {
            fontSize += 0.1;
            pageContent.style.fontSize = fontSize + "rem";
        }
    });

    // --- Sidebar Toggle ---
    btnToggleSidebar.addEventListener("click", function () {
        sidebar.classList.toggle("collapsed");
    });

    // --- Back to Upload ---
    btnBack.addEventListener("click", function () {
        stopAudio();
        bookData = null;
        readerSection.classList.add("hidden");
        uploadSection.classList.remove("hidden");
        resetUpload();
        document.title = "Cloud Book Reader - Leitor EPUB";
    });

    // --- Text-to-Speech ---
    btnTts.addEventListener("click", function () {
        if (isPlaying) {
            stopAudio();
            return;
        }

        if (!bookData) return;

        var chapter = bookData.chapters[currentChapter];
        var text = chapter.text;
        if (!text || text.trim().length === 0) {
            alert("Não há texto para ler neste capítulo.");
            return;
        }

        // Limit to 5000 chars (API limit)
        if (text.length > 5000) {
            text = text.substring(0, 5000);
        }

        isPlaying = true;
        btnTts.classList.add("active");
        btnTts.innerHTML = '<span class="loading-spinner"></span> Carregando...';

        var voiceType = document.getElementById("tts-voice-type").value;

        fetch("/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                text: text,
                language: ttsLanguage.value,
                voice_type: voiceType,
            }),
        })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.error) {
                    alert(data.error);
                    stopAudio();
                    return;
                }

                audioPlayer.src = "data:audio/mp3;base64," + data.audio;
                audioPlayer.play();

                btnTts.innerHTML =
                    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
                    '<rect x="6" y="4" width="4" height="16"></rect>' +
                    '<rect x="14" y="4" width="4" height="16"></rect>' +
                    "</svg> Parar";

                audioPlayer.addEventListener("ended", stopAudio, { once: true });
            })
            .catch(function () {
                alert("Erro ao conectar ao serviço de Text-to-Speech.");
                stopAudio();
            });
    });

    function stopAudio() {
        isPlaying = false;
        audioPlayer.pause();
        audioPlayer.currentTime = 0;
        btnTts.classList.remove("active");
        btnTts.innerHTML =
            '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
            '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>' +
            '<path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>' +
            "</svg> Ouvir";
    }

    // --- Utilities ---
    function escapeHtml(text) {
        var div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
})();
