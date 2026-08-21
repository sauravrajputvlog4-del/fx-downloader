// OmniStream HD Video & Audio Downloader Client Script

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const urlInput = document.getElementById('video-url-input');
    const clearInputBtn = document.getElementById('clear-input-btn');
    const pasteBtn = document.getElementById('paste-btn');
    const fetchBtn = document.getElementById('fetch-btn');
    const btnText = document.getElementById('btn-text');
    const btnIcon = document.getElementById('btn-icon');
    const btnSpinner = document.getElementById('btn-spinner');
    const errorBox = document.getElementById('error-box');
    const errorMessage = document.getElementById('error-message');

    // Input changes & Cut/Clear button
    urlInput.addEventListener('input', () => {
        if (urlInput.value.trim().length > 0) {
            clearInputBtn.classList.remove('hidden');
        } else {
            clearInputBtn.classList.add('hidden');
        }
    });

    if (clearInputBtn) {
        clearInputBtn.addEventListener('click', () => {
            urlInput.value = '';
            clearInputBtn.classList.add('hidden');
            hideError();
            urlInput.focus();
        });
    }

    // Paste from Clipboard
    pasteBtn.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                urlInput.value = text.trim();
                clearInputBtn.classList.remove('hidden');
                triggerFetch();
            }
        } catch (err) {
            urlInput.focus();
        }
    });
    // Folder Management Elements
    const currentSaveFolder = document.getElementById('current-save-folder');
    const changeFolderBtn = document.getElementById('change-folder-btn');
    const openFolderBtn = document.getElementById('open-folder-btn');
    const modalSavedFolder = document.getElementById('modal-saved-folder');
    const modalOpenFolderBtn = document.getElementById('modal-open-folder-btn');

    // Fetch and display current save folder
    async function loadSettings() {
        try {
            const res = await fetch('/api/settings');
            const data = await res.json();
            if (data.success && data.save_folder) {
                if (currentSaveFolder) currentSaveFolder.textContent = data.save_folder;
                if (modalSavedFolder) modalSavedFolder.textContent = data.save_folder;
            }
        } catch (e) {}
    }
    loadSettings();

    if (changeFolderBtn) {
        changeFolderBtn.addEventListener('click', async () => {
            changeFolderBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-[11px]"></i> Selecting...';
            try {
                const res = await fetch('/api/select-folder', { method: 'POST' });
                const data = await res.json();
                if (data.success && data.save_folder) {
                    if (currentSaveFolder) currentSaveFolder.textContent = data.save_folder;
                    if (modalSavedFolder) modalSavedFolder.textContent = data.save_folder;
                }
            } catch (e) {
            } finally {
                changeFolderBtn.innerHTML = '<i class="fa-solid fa-pen-to-square text-[11px]"></i> <span>Change Folder</span>';
            }
        });
    }

    if (openFolderBtn) {
        openFolderBtn.addEventListener('click', async () => {
            try {
                await fetch('/api/open-folder', { method: 'POST' });
            } catch (e) {}
        });
    }

    if (modalOpenFolderBtn) {
        modalOpenFolderBtn.addEventListener('click', async () => {
            try {
                await fetch('/api/open-folder', { method: 'POST' });
            } catch (e) {}
        });
    }

    const resultSection = document.getElementById('result-section');
    const resThumbnail = document.getElementById('res-thumbnail');
    const resDuration = document.getElementById('res-duration');
    const resPlatform = document.getElementById('res-platform');
    const resTitle = document.getElementById('res-title');
    const resUploader = document.getElementById('res-uploader');
    const resViews = document.getElementById('res-views');
    const resOriginLink = document.getElementById('res-origin-link');
    const tabVideoBtn = document.getElementById('tab-video-btn');
    const tabAudioBtn = document.getElementById('tab-audio-btn');
    const videoOptionsContainer = document.getElementById('video-options-container');
    const audioOptionsContainer = document.getElementById('audio-options-container');

    // Progress Modal Elements
    const progressModal = document.getElementById('progress-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalSubtitle = document.getElementById('modal-subtitle');
    const modalStatusText = document.getElementById('modal-status-text');
    const modalPercent = document.getElementById('modal-percent');
    const modalBar = document.getElementById('modal-bar');
    const modalSpeed = document.getElementById('modal-speed');
    const modalEta = document.getElementById('modal-eta');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalSpinner = document.getElementById('modal-spinner');
    const modalActionBox = document.getElementById('modal-action-box');
    const saveFileBtn = document.getElementById('save-file-btn');

    // History Elements
    const historyToggleBtn = document.getElementById('history-toggle-btn');
    const historyDrawer = document.getElementById('history-drawer');
    const closeHistoryBtn = document.getElementById('close-history-btn');
    const historyList = document.getElementById('history-list');
    const clearHistoryBtn = document.getElementById('clear-history-btn');
    const historyBadge = document.getElementById('history-badge');

    let currentVideoData = null;
    let activeEventSource = null;

    // Paste from Clipboard
    pasteBtn.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                urlInput.value = text.trim();
                triggerFetch();
            }
        } catch (err) {
            urlInput.focus();
        }
    });

    // Enter Key on Input
    urlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            triggerFetch();
        }
    });

    // Fetch Video Info
    fetchBtn.addEventListener('click', triggerFetch);

    async function triggerFetch() {
        const url = urlInput.value.trim();
        if (!url) {
            showError('Please paste or type a valid video link first.');
            return;
        }

        hideError();
        setLoading(true);
        resultSection.classList.add('hidden');

        try {
            const res = await fetch('/api/info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });

            const data = await res.json();
            if (!res.ok || !data.success) {
                throw new Error(data.error || 'Failed to fetch video details.');
            }

            currentVideoData = data;
            renderVideoDetails(data);
        } catch (err) {
            showError(err.message || 'Unable to process video link. Please verify the URL.');
        } finally {
            setLoading(false);
        }
    }

    function renderVideoDetails(data) {
        resThumbnail.src = data.thumbnail || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&q=80';
        resDuration.textContent = data.duration_str || 'Live / Clip';
        resPlatform.textContent = data.platform || 'Video';
        resTitle.textContent = data.title || 'Untitled Video';
        resUploader.textContent = data.uploader || 'Creator';
        resViews.textContent = data.view_count || 'N/A';
        resOriginLink.href = data.url || '#';

        // Render Video Resolutions
        videoOptionsContainer.innerHTML = '';
        if (data.video_options && data.video_options.length > 0) {
            data.video_options.forEach(opt => {
                const is4k = opt.quality_tag.includes('4K');
                const is2k = opt.quality_tag.includes('2K');
                const is1080 = opt.quality_tag.includes('1080');

                let badgeColor = 'bg-slate-800 text-slate-300 border-slate-700';
                if (is4k) badgeColor = 'bg-cyan-500 text-black font-black shadow-md shadow-cyan-500/30';
                else if (is2k) badgeColor = 'bg-purple-500 text-white font-bold';
                else if (is1080) badgeColor = 'bg-indigo-500/30 text-indigo-300 border-indigo-500/40 font-bold';

                const card = document.createElement('div');
                card.className = 'quality-card p-4 rounded-2xl bg-slate-950/70 border border-slate-800/80 flex flex-col justify-between gap-3';
                card.innerHTML = `
                    <div class="flex items-start justify-between">
                        <div>
                            <span class="px-2.5 py-1 rounded-lg text-xs ${badgeColor}">
                                ${opt.quality_tag}
                            </span>
                            <h5 class="font-bold text-white font-['Outfit'] text-base mt-2.5">
                                ${opt.label}
                            </h5>
                            <p class="text-xs text-slate-400 mt-0.5">Format: ${opt.ext.toUpperCase()} &bull; ${opt.filesize_str}</p>
                        </div>
                    </div>
                    <button class="download-trigger-btn w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white font-bold text-sm shadow-md shadow-cyan-500/20 flex items-center justify-center gap-2 transition-all active:scale-95"
                        data-type="video"
                        data-quality="${opt.height || '1080'}"
                        data-format-id="${opt.format_id}">
                        <i class="fa-solid fa-download text-xs"></i>
                        <span>Download MP4</span>
                    </button>
                `;
                videoOptionsContainer.appendChild(card);
            });
        }

        // Render Audio Options
        audioOptionsContainer.innerHTML = '';
        if (data.audio_options && data.audio_options.length > 0) {
            data.audio_options.forEach(opt => {
                const card = document.createElement('div');
                card.className = 'quality-card p-4 rounded-2xl bg-slate-950/70 border border-slate-800/80 flex flex-col justify-between gap-3';
                card.innerHTML = `
                    <div class="flex items-start justify-between">
                        <div>
                            <span class="px-2.5 py-1 rounded-lg text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-bold">
                                ${opt.tag}
                            </span>
                            <h5 class="font-bold text-white font-['Outfit'] text-base mt-2.5">
                                ${opt.label}
                            </h5>
                            <p class="text-xs text-slate-400 mt-0.5">Bitrate: ${opt.quality} &bull; Audio</p>
                        </div>
                    </div>
                    <button class="download-trigger-btn w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-bold text-sm shadow-md shadow-emerald-500/20 flex items-center justify-center gap-2 transition-all active:scale-95"
                        data-type="audio"
                        data-quality="${opt.quality}"
                        data-format-id="${opt.format_id}">
                        <i class="fa-solid fa-music text-xs"></i>
                        <span>Download ${opt.ext.toUpperCase()}</span>
                    </button>
                `;
                audioOptionsContainer.appendChild(card);
            });
        }

        // Attach download button listeners
        document.querySelectorAll('.download-trigger-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const type = btn.getAttribute('data-type');
                const quality = btn.getAttribute('data-quality');
                const formatId = btn.getAttribute('data-format-id');
                startDownloadProcess(type, quality, formatId);
            });
        });

        // Show results
        resultSection.classList.remove('hidden');
        resultSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // Tab Switching
    tabVideoBtn.addEventListener('click', () => {
        tabVideoBtn.className = "px-5 py-2.5 rounded-xl font-['Outfit'] font-bold text-sm bg-gradient-to-r from-cyan-500 to-indigo-600 text-white shadow-md shadow-cyan-500/20 flex items-center gap-2 transition-all";
        tabAudioBtn.className = "px-5 py-2.5 rounded-xl font-['Outfit'] font-bold text-sm bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 flex items-center gap-2 transition-all";
        videoOptionsContainer.classList.remove('hidden');
        audioOptionsContainer.classList.add('hidden');
    });

    tabAudioBtn.addEventListener('click', () => {
        tabAudioBtn.className = "px-5 py-2.5 rounded-xl font-['Outfit'] font-bold text-sm bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-md shadow-emerald-500/20 flex items-center gap-2 transition-all";
        tabVideoBtn.className = "px-5 py-2.5 rounded-xl font-['Outfit'] font-bold text-sm bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 flex items-center gap-2 transition-all";
        audioOptionsContainer.classList.remove('hidden');
        videoOptionsContainer.classList.add('hidden');
    });

    // Start Download Process
    async function startDownloadProcess(type, quality, formatId) {
        if (!currentVideoData) return;

        openProgressModal(type, quality);

        try {
            const res = await fetch('/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: currentVideoData.url,
                    type: type,
                    quality: quality,
                    format_id: formatId
                })
            });

            const data = await res.json();
            if (!res.ok || !data.success) {
                throw new Error(data.error || 'Could not initiate download stream.');
            }

            listenToProgress(data.task_id);
        } catch (err) {
            updateModalError(err.message || 'Error occurred starting download.');
        }
    }

    function openProgressModal(type, quality) {
        modalTitle.textContent = type === 'audio' ? 'Extracting High Quality Audio' : 'Downloading HD Video Stream';
        modalSubtitle.textContent = `Target: ${quality} lossless format`;
        modalStatusText.textContent = 'Initializing connection...';
        modalPercent.textContent = '0%';
        modalBar.style.width = '0%';
        modalSpeed.textContent = 'Connecting...';
        modalEta.textContent = 'Estimating...';
        modalActionBox.classList.add('hidden');
        modalSpinner.className = 'fa-solid fa-circle-notch fa-spin text-lg';
        progressModal.classList.remove('hidden');
    }

    function listenToProgress(taskId) {
        if (activeEventSource) {
            activeEventSource.close();
        }

        activeEventSource = new EventSource(`/api/progress/${taskId}`);
        window.activeEventSource = activeEventSource;

        activeEventSource.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);

                if (data.status === 'downloading') {
                    const percent = Math.min(data.percent || 0, 95);
                    modalPercent.textContent = `${percent}%`;
                    modalBar.style.width = `${percent}%`;
                    modalStatusText.textContent = 'Downloading high-resolution streams...';
                    modalSpeed.textContent = data.speed || 'High Speed';
                    modalEta.textContent = data.eta || '--';
                } else if (data.status === 'processing') {
                    modalPercent.textContent = '98%';
                    modalBar.style.width = '98%';
                    modalStatusText.textContent = 'Merging video & audio with FFmpeg...';
                    modalSpeed.textContent = 'Processing...';
                    modalEta.textContent = 'A few seconds';
                } else if (data.status === 'completed') {
                    activeEventSource.close();
                    modalPercent.textContent = '100%';
                    modalBar.style.width = '100%';
                    modalStatusText.textContent = 'Ready! Download completed.';
                    modalSpeed.textContent = 'Done';
                    modalEta.textContent = '0s';
                    modalSpinner.className = 'fa-solid fa-circle-check text-emerald-400 text-lg';

                    const downloadUrl = `/api/get-file/${encodeURIComponent(data.file_id)}?name=${encodeURIComponent(data.filename || 'video.mp4')}`;
                    saveFileBtn.href = downloadUrl;
                    if (modalSavedFolder && data.save_folder) {
                        modalSavedFolder.textContent = data.save_folder;
                    }
                    modalActionBox.classList.remove('hidden');

                    // Automatically trigger browser download
                    const autoLink = document.createElement('a');
                    autoLink.href = downloadUrl;
                    autoLink.setAttribute('download', data.filename || 'video.mp4');
                    document.body.appendChild(autoLink);
                    autoLink.click();
                    document.body.removeChild(autoLink);

                    fetchHistory();
                } else if (data.status === 'error') {
                    activeEventSource.close();
                    updateModalError(data.error || 'Download failed during extraction.');
                }
            } catch (err) {
                console.error(err);
            }
        };

        activeEventSource.onerror = () => {
            // Polling fallback
            if (activeEventSource) {
                activeEventSource.close();
            }
            fallbackPoll(taskId);
        };
    }

    async function fallbackPoll(taskId) {
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/task-status/${taskId}`);
                const data = await res.json();
                if (data.status === 'completed') {
                    clearInterval(interval);
                    modalPercent.textContent = '100%';
                    modalBar.style.width = '100%';
                    modalStatusText.textContent = 'Ready! Download completed.';
                    modalSpinner.className = 'fa-solid fa-circle-check text-emerald-400 text-lg';

                    const downloadUrl = `/api/get-file/${encodeURIComponent(data.file_id)}`;
                    saveFileBtn.href = downloadUrl;
                    modalActionBox.classList.remove('hidden');

                    window.location.href = downloadUrl;
                    fetchHistory();
                } else if (data.status === 'error') {
                    clearInterval(interval);
                    updateModalError(data.error || 'Download failed.');
                } else {
                    const percent = Math.min(data.percent || 20, 95);
                    modalPercent.textContent = `${percent}%`;
                    modalBar.style.width = `${percent}%`;
                }
            } catch (err) {
                clearInterval(interval);
            }
        }, 1000);
    }

    function updateModalError(msg) {
        modalStatusText.textContent = 'Error occurred';
        modalPercent.textContent = 'Failed';
        modalSpeed.textContent = 'Stopped';
        modalSpinner.className = 'fa-solid fa-triangle-exclamation text-rose-500 text-lg';
        modalSubtitle.textContent = msg;
    }

    function closeModal() {
        if (activeEventSource) {
            activeEventSource.close();
            activeEventSource = null;
        }
        progressModal.classList.add('hidden');
    }

    if (modalCloseBtn) {
        modalCloseBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            closeModal();
        });
    }

    const modalDoneCloseBtn = document.getElementById('modal-done-close-btn');
    if (modalDoneCloseBtn) {
        modalDoneCloseBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            closeModal();
        });
    }

    // Click outside modal to close
    progressModal.addEventListener('click', (e) => {
        if (e.target === progressModal) {
            closeModal();
        }
    });

    // Escape key closes modal & drawer
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
            historyDrawer.classList.add('translate-x-full');
        }
    });

    // History Drawer Logic
    historyToggleBtn.addEventListener('click', () => {
        historyDrawer.classList.remove('translate-x-full');
        fetchHistory();
    });

    closeHistoryBtn.addEventListener('click', () => {
        historyDrawer.classList.add('translate-x-full');
    });

    clearHistoryBtn.addEventListener('click', async () => {
        try {
            await fetch('/api/clear-history', { method: 'POST' });
            fetchHistory();
        } catch (e) {}
    });

    async function fetchHistory() {
        try {
            const res = await fetch('/api/history');
            const data = await res.json();
            if (data.success && data.history) {
                renderHistory(data.history);
            }
        } catch (e) {}
    }

    function renderHistory(items) {
        if (items.length > 0) {
            historyBadge.textContent = items.length;
            historyBadge.classList.remove('hidden');
        } else {
            historyBadge.classList.add('hidden');
        }

        if (items.length === 0) {
            historyList.innerHTML = `
                <div class="text-center py-16 text-slate-500 text-sm">
                    <i class="fa-solid fa-inbox text-3xl mb-2 block text-slate-600"></i>
                    No downloaded videos yet
                </div>
            `;
            return;
        }

        historyList.innerHTML = '';
        items.forEach(item => {
            const div = document.createElement('div');
            div.className = 'p-3.5 rounded-2xl bg-slate-950/60 border border-slate-800/80 flex items-center justify-between gap-3 hover:border-slate-700 transition-colors';
            div.innerHTML = `
                <div class="flex items-center gap-3 min-w-0">
                    <div class="w-10 h-10 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center shrink-0 text-cyan-400">
                        <i class="${item.type === 'audio' ? 'fa-solid fa-music' : 'fa-solid fa-video'} text-sm"></i>
                    </div>
                    <div class="min-w-0">
                        <h6 class="text-xs font-bold text-white truncate">${item.title}</h6>
                        <p class="text-[11px] text-slate-400">${item.quality} &bull; ${item.size} &bull; ${item.timestamp}</p>
                    </div>
                </div>
                <a href="/api/get-file/${encodeURIComponent(item.file_id)}" download class="px-3 py-1.5 rounded-xl bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 text-xs font-bold shrink-0 border border-cyan-500/30 flex items-center gap-1.5 transition-colors">
                    <i class="fa-solid fa-download text-[10px]"></i>
                    <span>Save</span>
                </a>
            `;
            historyList.appendChild(div);
        });
    }

    // Initial History Load
    fetchHistory();

    // Helpers
    function setLoading(isLoading) {
        if (isLoading) {
            btnText.textContent = 'Inspecting...';
            btnIcon.classList.add('hidden');
            btnSpinner.classList.remove('hidden');
            fetchBtn.disabled = true;
            fetchBtn.classList.add('opacity-80');
        } else {
            btnText.textContent = 'Fetch Video';
            btnIcon.classList.remove('hidden');
            btnSpinner.classList.add('hidden');
            fetchBtn.disabled = false;
            fetchBtn.classList.remove('opacity-80');
        }
    }

    function showError(msg) {
        errorMessage.textContent = msg;
        errorBox.classList.remove('hidden');
    }

    function hideError() {
        errorBox.classList.add('hidden');
    }
});
