/**
 * Gemini Book Reader — Frontend
 * Leitor de TXT com Gemini 2.5 Flash TTS
 */
(function () {
    "use strict";

    var bookData = null, currentPage = 0, fontSize = 1.12, isPlaying = false, autoMode = false;

    var screenUpload = document.getElementById("screen-upload");
    var screenReader = document.getElementById("screen-reader");
    var dropZone = document.getElementById("drop-zone");
    var fileInput = document.getElementById("file-input");
    var btnSelect = document.getElementById("btn-select");
    var progressArea = document.getElementById("upload-progress");
    var progressBar = document.getElementById("progress-bar");
    var progressText = document.getElementById("progress-text");
    var readerText = document.getElementById("reader-text");
    var readerBody = document.getElementById("reader-body");
    var fileNameEl = document.getElementById("file-name");
    var curPage = document.getElementById("cur-page");
    var totPages = document.getElementById("tot-pages");
    var btnBack = document.getElementById("btn-back");
    var btnPrev = document.getElementById("btn-prev");
    var btnNext = document.getElementById("btn-next");
    var btnFontDown = document.getElementById("btn-font-down");
    var btnFontUp = document.getElementById("btn-font-up");
    var selStyle = document.getElementById("sel-style");
    var selLanguage = document.getElementById("sel-language");
    var btnSpeak = document.getElementById("btn-speak");
    var btnAuto = document.getElementById("btn-auto");
    var speakLabel = document.getElementById("speak-label");
    var iconPlay = document.getElementById("icon-play");
    var iconStop = document.getElementById("icon-stop");
    var audioEl = document.getElementById("audio-el");
    var audioBarWrap = document.getElementById("audio-bar-wrap");
    var audioFill = document.getElementById("audio-fill");
    var audioTime = document.getElementById("audio-time");
    var btnTheme = document.getElementById("btn-theme");

    // Theme
    function initTheme() {
        var s = localStorage.getItem("gem-theme");
        if (s === "dark" || (!s && window.matchMedia("(prefers-color-scheme: dark)").matches)) setDark(true);
    }
    function setDark(on) {
        if (on) document.documentElement.setAttribute("data-theme", "dark");
        else document.documentElement.removeAttribute("data-theme");
        document.getElementById("icon-light").classList.toggle("hidden", on);
        document.getElementById("icon-dark").classList.toggle("hidden", !on);
        localStorage.setItem("gem-theme", on ? "dark" : "light");
    }
    btnTheme.addEventListener("click", function () { setDark(document.documentElement.getAttribute("data-theme") !== "dark"); });
    initTheme();

    // Upload
    btnSelect.addEventListener("click", function () { fileInput.click(); });
    dropZone.addEventListener("click", function (e) { if (e.target !== btnSelect && !btnSelect.contains(e.target)) fileInput.click(); });
    dropZone.addEventListener("dragover", function (e) { e.preventDefault(); dropZone.classList.add("dragover"); });
    dropZone.addEventListener("dragleave", function () { dropZone.classList.remove("dragover"); });
    dropZone.addEventListener("drop", function (e) { e.preventDefault(); dropZone.classList.remove("dragover"); if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]); });
    fileInput.addEventListener("change", function () { if (fileInput.files.length) handleFile(fileInput.files[0]); });

    function handleFile(f) {
        if (!f.name.toLowerCase().endsWith(".txt")) { alert("Selecione um .txt"); return; }
        if (f.size > 20 * 1024 * 1024) { alert("Excede 20MB."); return; }
        upload(f);
    }

    function upload(file) {
        dropZone.classList.add("hidden");
        progressArea.classList.remove("hidden");
        progressBar.style.width = "15%";
        progressText.textContent = "Enviando...";
        var fd = new FormData(); fd.append("file", file);
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "/upload", true);
        xhr.upload.addEventListener("progress", function (e) { if (e.lengthComputable) progressBar.style.width = Math.round((e.loaded / e.total) * 70 + 15) + "%"; });
        xhr.addEventListener("load", function () {
            if (xhr.status === 200) { progressBar.style.width = "100%"; progressText.textContent = "Pronto!"; setTimeout(function () { openBook(JSON.parse(xhr.responseText)); }, 200); }
            else { var err = JSON.parse(xhr.responseText); progressText.textContent = "Erro: " + (err.error || "Falha"); setTimeout(resetUpload, 2000); }
        });
        xhr.addEventListener("error", function () { progressText.textContent = "Erro de conexão."; setTimeout(resetUpload, 2000); });
        xhr.send(fd);
    }

    function resetUpload() { dropZone.classList.remove("hidden"); progressArea.classList.add("hidden"); progressBar.style.width = "0%"; fileInput.value = ""; }

    function openBook(data) {
        bookData = data; currentPage = 0;
        fileNameEl.textContent = data.filename; totPages.textContent = data.total_pages;
        document.title = data.filename + " — Gemini Reader";
        screenUpload.classList.add("hidden"); screenReader.classList.remove("hidden");
        renderPage(0);
    }

    function renderPage(idx) {
        if (!bookData || idx < 0 || idx >= bookData.pages.length) return;
        currentPage = idx; readerText.textContent = bookData.pages[idx];
        curPage.textContent = idx + 1; readerBody.scrollTop = 0; stopAudio();
    }

    btnPrev.addEventListener("click", function () { if (currentPage > 0) renderPage(currentPage - 1); });
    btnNext.addEventListener("click", function () { if (bookData && currentPage < bookData.pages.length - 1) renderPage(currentPage + 1); });
    document.addEventListener("keydown", function (e) {
        if (!bookData || e.target.tagName === "SELECT") return;
        if (e.key === "ArrowLeft" && currentPage > 0) { e.preventDefault(); renderPage(currentPage - 1); }
        if (e.key === "ArrowRight" && bookData && currentPage < bookData.pages.length - 1) { e.preventDefault(); renderPage(currentPage + 1); }
        if (e.key === " " && e.target.tagName !== "BUTTON") { e.preventDefault(); btnSpeak.click(); }
    });

    btnFontDown.addEventListener("click", function () { if (fontSize > 0.85) { fontSize -= 0.08; readerText.style.fontSize = fontSize + "rem"; } });
    btnFontUp.addEventListener("click", function () { if (fontSize < 2.0) { fontSize += 0.08; readerText.style.fontSize = fontSize + "rem"; } });
    btnBack.addEventListener("click", function () { stopAudio(); autoMode = false; btnAuto.classList.remove("active"); bookData = null; screenReader.classList.add("hidden"); screenUpload.classList.remove("hidden"); resetUpload(); document.title = "Gemini Reader"; });

    // Auto
    btnAuto.addEventListener("click", function () { autoMode = !autoMode; btnAuto.classList.toggle("active", autoMode); if (autoMode && !isPlaying) btnSpeak.click(); });

    // TTS
    btnSpeak.addEventListener("click", function () {
        if (isPlaying) { stopAudio(); return; }
        if (!bookData) return;
        var text = bookData.pages[currentPage];
        if (!text || !text.trim()) { alert("Página vazia."); return; }

        isPlaying = true; btnSpeak.classList.add("playing");
        iconPlay.classList.add("hidden"); iconStop.classList.add("hidden");
        speakLabel.innerHTML = '<span class="spinner"></span> Gerando com Gemini...';

        fetch("/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text, style: selStyle.value, language: selLanguage.value }),
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.error) { alert(data.error); stopAudio(); return; }
            audioEl.src = "data:audio/wav;base64," + data.audio;
            audioEl.play();
            iconPlay.classList.add("hidden"); iconStop.classList.remove("hidden");
            speakLabel.textContent = "Parar"; audioBarWrap.classList.remove("hidden");
            audioEl.addEventListener("ended", onEnd, { once: true });
        })
        .catch(function () { alert("Erro ao gerar áudio."); stopAudio(); });
    });

    function onEnd() {
        stopAudio();
        if (autoMode && bookData && currentPage < bookData.pages.length - 1) { renderPage(currentPage + 1); setTimeout(function () { btnSpeak.click(); }, 500); }
        else if (autoMode) { autoMode = false; btnAuto.classList.remove("active"); }
    }

    audioEl.addEventListener("timeupdate", function () {
        if (!audioEl.duration) return;
        audioFill.style.width = (audioEl.currentTime / audioEl.duration * 100) + "%";
        var m = Math.floor(audioEl.currentTime / 60), s = Math.floor(audioEl.currentTime % 60);
        audioTime.textContent = m + ":" + (s < 10 ? "0" : "") + s;
    });

    function stopAudio() {
        isPlaying = false; audioEl.pause(); audioEl.currentTime = 0;
        btnSpeak.classList.remove("playing"); iconPlay.classList.remove("hidden"); iconStop.classList.add("hidden");
        speakLabel.textContent = "Ouvir Página"; audioBarWrap.classList.add("hidden"); audioFill.style.width = "0%"; audioTime.textContent = "0:00";
    }
})();
