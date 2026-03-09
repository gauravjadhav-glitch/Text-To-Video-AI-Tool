// ═══════════════════════════════════════════════════════════════════
//  VIRAL IDEAS HANDLER
// ═══════════════════════════════════════════════════════════════════
const viralBtn = document.getElementById('get-viral-btn');
const autoRunBtn = document.getElementById('auto-run-btn');
const viralNiche = document.getElementById('viral-niche');
const viralList = document.getElementById('viral-ideas-list');

if (viralBtn) {
    viralBtn.addEventListener('click', async () => {
        const niche = viralNiche.value;
        viralBtn.innerText = "Loading...";
        viralBtn.disabled = true;

        try {
            const response = await fetch(`${API_BASE_URL}/viral-ideas?niche=${niche}`);
            const data = await response.json();

            if (data.status === "success") {
                viralList.innerHTML = '';
                data.topics.forEach(topic => {
                    const div = document.createElement('div');
                    div.className = 'idea-item';
                    div.innerText = topic;
                    div.addEventListener('click', () => {
                        textarea.value = topic;
                        viralList.classList.add('hidden');
                    });
                    viralList.appendChild(div);
                });
                viralList.classList.remove('hidden');
            }
        } catch (err) {
            console.error("Failed to fetch viral ideas:", err);
        } finally {
            viralBtn.innerText = "Fetch Ideas";
            viralBtn.disabled = false;
        }
    });
}

// One-click: Idea -> Documentary -> Upload
if (autoRunBtn) {
    autoRunBtn.addEventListener('click', async () => {
        const niche = viralNiche.value;
        const docDurValEl = document.querySelector('input[name="doc_duration"]:checked');
        const docDurVal = docDurValEl ? docDurValEl.value : "120";

        const cleanupAutoRunUI = () => {
            radarBox.classList.remove('active');
            stepProgress.classList.add('hidden');
            timerContainer.classList.add('hidden');
        };

        const showAutoRunError = (message) => {
            // Hide the overlay/progress UI per UX expectation for failures.
            statusOverlay.classList.add('hidden');
            stepProgress.classList.add('hidden');
            radarBox.classList.remove('active');
            timerContainer.classList.add('hidden');

            if (uploadStatus) {
                uploadStatus.classList.remove('hidden');
                uploadStatus.style.color = "#ef4444";
                uploadStatus.innerText = message || "Auto run failed.";
            } else {
                // Fallback: keep overlay visible if uploadStatus is missing
                statusOverlay.classList.remove('hidden');
                statusText.innerText = "Auto Run Failed";
                statusSubtext.innerText = message || "Auto run failed.";
                statusSubtext.style.color = "#ef4444";
            }
        };

        // Reset UI State (reuse the same overlay)
        btn.classList.add('loading');
        btn.disabled = true;
        autoRunBtn.disabled = true;
        viralBtn && (viralBtn.disabled = true);

        videoResult.classList.add('hidden');
        scriptBox.classList.add('hidden');
        statusOverlay.classList.remove('hidden');
        radarBox.classList.add('active');
        timerContainer.classList.remove('hidden');
        stepProgress.classList.remove('hidden');

        statusSubtext.innerText = "Auto-running: viral idea → documentary → render → YouTube upload.";
        updateStep(1, "Picking Viral Idea...");

        // Start Timer
        let startTime = Date.now();
        let timerInterval = setInterval(() => {
            let elapsedTime = Date.now() - startTime;
            let seconds = Math.floor(elapsedTime / 1000);
            let minutes = Math.floor(seconds / 60);
            seconds = seconds % 60;
            timerValue.innerText = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);

        // Simulate step progress while waiting
        const stepTimer = setInterval(() => {
            const elapsed = (Date.now() - startTime) / 1000;
            if (elapsed > 3 && elapsed < 20) {
                updateStep(2, "Writing Documentary Script...");
                statusSubtext.innerText = "Generating Hindi script + visuals prompts.";
            } else if (elapsed > 20 && elapsed < 50) {
                updateStep(3, "Recording Voiceover...");
                statusSubtext.innerText = "Generating narration and captions.";
            } else if (elapsed > 50 && elapsed < 90) {
                updateStep(4, "Assembling Final Video...");
                statusSubtext.innerText = "Rendering video and preparing upload.";
            } else if (elapsed > 90) {
                updateStep(5, "Uploading to YouTube...");
                statusSubtext.innerText = "OAuth window may open for authorization.";
            }
        }, 2000);

        try {
            const fd = new FormData();
            fd.append("niche", niche);
            fd.append("duration", docDurVal);
            fd.append("privacy_status", "public");

            const res = await fetch(`${API_BASE_URL}/auto-documentary-upload`, { method: "POST", body: fd });
            const data = await res.json();
            clearInterval(stepTimer);

            if (res.ok && data.status === "success") {
                clearInterval(timerInterval);
                updateStep(5, "Uploaded!");
                statusSubtext.innerText = `YouTube Video ID: ${data.video_id}`;

                setTimeout(() => {
                    statusOverlay.classList.add('hidden');
                    stepProgress.classList.add('hidden');
                    videoResult.classList.remove('hidden');
                    finalTimeValue.innerText = timerValue.innerText;

                    if (data.script_used) {
                        scriptBox.classList.remove('hidden');
                        scriptUsedText.innerText = data.script_used;
                    }

                    textarea.value = data.topic || textarea.value;
                    videoPreview.src = `${API_BASE_URL}${data.video_url}`;
                    downloadBtn.href = `${API_BASE_URL}${data.video_url}`;
                    downloadBtn.setAttribute('download', 'rendered_video.mp4');

                    if (uploadStatus) {
                        uploadStatus.classList.remove('hidden');
                        uploadStatus.style.color = "#22c55e";
                        uploadStatus.innerText = `Uploaded! Video ID: ${data.video_id}`;
                    }
                }, 800);
            } else {
                cleanupAutoRunUI();
                showAutoRunError(data.message || "Check API keys / OAuth setup.");
            }
        } catch (e) {
            cleanupAutoRunUI();
            showAutoRunError("Server is unreachable. Please try again.");
        } finally {
            clearInterval(stepTimer);
            clearInterval(timerInterval);
            btn.classList.remove('loading');
            btn.disabled = false;
            autoRunBtn.disabled = false;
            viralBtn && (viralBtn.disabled = false);
        }
    });
}
// Production URL (Update this with your actual Render URL if using separate deployment)
const RENDER_BACKEND_URL = "https://text-to-video-ai-tool.onrender.com";

const API_BASE_URL = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://localhost:8000"
    : (window.location.origin.includes("vercel.app") ? RENDER_BACKEND_URL : window.location.origin);

// ═══════════════════════════════════════════════════════════════════
//  SELECT ELEMENTS
// ═══════════════════════════════════════════════════════════════════
const form = document.getElementById('generate-form');
const btn = document.getElementById('generate-btn');
const textarea = document.getElementById('input_text');
const modeRadios = document.querySelectorAll('input[name="mode"]');
const statusOverlay = document.getElementById('status-overlay');
const statusText = document.getElementById('status-text');
const statusSubtext = document.getElementById('status-subtext');
const videoResult = document.getElementById('video-result');
const radarBox = document.querySelector('.radar-box');
const videoPreview = document.getElementById('preview-video');
const downloadBtn = document.getElementById('download-btn');
const uploadYoutubeBtn = document.getElementById('upload-youtube-btn');
const uploadStatus = document.getElementById('upload-status');
const timerContainer = document.getElementById('timer-container');
const timerValue = document.getElementById('timer-value');
const scriptBox = document.getElementById('final-script-display');
const scriptUsedText = document.getElementById('script-used-text');
const finalTimeValue = document.getElementById('final-time-value');

const typeShorts = document.getElementById('typeShorts');
const typeDoc = document.getElementById('typeDoc');
const shortsDuration = document.getElementById('shorts-duration');
const docDuration = document.getElementById('doc-duration');
const modeGroup = document.getElementById('mode-group');
const mediaOptions = document.getElementById('media-options');
const docInfoBox = document.getElementById('doc-info-box');
const languageGroup = document.getElementById('language-group');
const stepProgress = document.getElementById('step-progress');

// ═══════════════════════════════════════════════════════════════════
//  VIDEO TYPE SWITCH: Shorts ↔ Documentary
// ═══════════════════════════════════════════════════════════════════
document.querySelectorAll('input[name="video_type"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        const isDoc = e.target.value === 'documentary';

        // Toggle duration controls
        shortsDuration.style.display = isDoc ? 'none' : '';
        docDuration.style.display = isDoc ? 'grid' : 'none';
        if (isDoc) {
            docDuration.style.gridTemplateColumns = 'repeat(3, 1fr)';
            docDuration.style.gap = '5px';
        }

        // Hide mode group for documentary (always auto-generate)
        modeGroup.style.display = isDoc ? 'none' : '';

        // Hide media options for documentary (always uses AI images)
        mediaOptions.style.display = isDoc ? 'none' : '';

        // Hide language for documentary (always Hindi)
        languageGroup.style.display = isDoc ? 'none' : '';

        // Show/hide documentary info box
        if (isDoc) {
            docInfoBox.classList.remove('hidden');
        } else {
            docInfoBox.classList.add('hidden');
        }

        // For documentary, auto-select Hindi and lock
        if (isDoc) {
            document.getElementById('langHin').checked = true;
            textarea.placeholder = "E.g., Jallianwala Bagh Massacre, Battle of Panipat, Partition of India...";
            btn.querySelector('.btn-text').innerText = 'Build Documentary';
        } else {
            textarea.placeholder = "E.g., Marathi facts about Indian kings...";
            btn.querySelector('.btn-text').innerText = 'Build My Video';
        }
    });
});

// ═══════════════════════════════════════════════════════════════════
//  DYNAMIC PLACEHOLDER (Shorts mode)
// ═══════════════════════════════════════════════════════════════════
modeRadios.forEach(radio => {
    radio.addEventListener('change', (e) => {
        if (typeDoc.checked) return;  // Don't change if in documentary mode
        if (e.target.value === 'topic') {
            textarea.placeholder = "E.g., 5 mind-blowing facts about space in Marathi...";
        } else {
            textarea.placeholder = "Paste your full 60s script here (Marathi supported)...";
        }
    });
});

// ═══════════════════════════════════════════════════════════════════
//  MUTUALLY EXCLUSIVE CHECKBOXES
// ═══════════════════════════════════════════════════════════════════
const aiCheckbox = document.getElementById('use_ai_images');
const stockCheckbox = document.getElementById('use_stock_images');

if (aiCheckbox && stockCheckbox) {
    aiCheckbox.addEventListener('change', () => {
        if (aiCheckbox.checked) stockCheckbox.checked = false;
    });
    stockCheckbox.addEventListener('change', () => {
        if (stockCheckbox.checked) aiCheckbox.checked = false;
    });
}

// ═══════════════════════════════════════════════════════════════════
//  STEP PROGRESS HELPER (Documentary mode)
// ═══════════════════════════════════════════════════════════════════
function updateStep(stepNum, text) {
    // Reset all steps
    for (let i = 1; i <= 5; i++) {
        const el = document.getElementById(`step-${i}`);
        if (!el) continue;
        el.classList.remove('active', 'done');
        if (i < stepNum) el.classList.add('done');
        if (i === stepNum) el.classList.add('active');
    }
    if (text) {
        statusText.innerText = text;
    }
}

// ═══════════════════════════════════════════════════════════════════
//  FORM SUBMISSION — handles both Shorts & Documentary
// ═══════════════════════════════════════════════════════════════════
form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const isDocumentary = typeDoc.checked;

    // Reset UI State
    btn.classList.add('loading');
    btn.disabled = true;
    btn.querySelector('.btn-text').innerText = 'Processing...';

    videoResult.classList.add('hidden');
    scriptBox.classList.add('hidden');
    statusOverlay.classList.remove('hidden');
    radarBox.classList.add('active');
    timerContainer.classList.remove('hidden');

    // Show step progress for documentary
    if (isDocumentary) {
        stepProgress.classList.remove('hidden');
        updateStep(1, "Writing Documentary Script...");
        statusSubtext.innerText = "AI is crafting a suspenseful Hindi script with strong hooks.";
    } else {
        stepProgress.classList.add('hidden');
        statusText.innerText = "Processing Idea...";
        statusSubtext.innerText = "Generating script, voiceover, and visual content. Please hold on.";
    }

    // Start Timer
    let startTime = Date.now();
    let timerInterval = setInterval(() => {
        let elapsedTime = Date.now() - startTime;
        let seconds = Math.floor(elapsedTime / 1000);
        let minutes = Math.floor(seconds / 60);
        seconds = seconds % 60;
        timerValue.innerText = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }, 1000);

    // Prepare Payload
    const language = document.querySelector('input[name="language"]:checked').value;

    const formData = new FormData();
    formData.append('input_text', textarea.value);
    formData.append('language', language);

    if (isDocumentary) {
        formData.append('mode', 'documentary');
        const docDurVal = document.querySelector('input[name="doc_duration"]:checked').value;
        formData.append('duration', docDurVal);
        formData.append('use_ai_images', true);
        formData.append('use_stock_images', false);
    } else {
        const duration = document.querySelector('input[name="duration"]:checked').value;
        const mode = document.querySelector('input[name="mode"]:checked').value;
        formData.append('mode', mode);
        formData.append('duration', duration);
        formData.append('use_ai_images', aiCheckbox.checked);
        formData.append('use_stock_images', stockCheckbox.checked);
    }

    try {
        // For documentary, we use SSE-style polling (updates come through regular response)
        if (isDocumentary) {
            // Simulate step progress while waiting
            const stepTimer = setInterval(() => {
                const elapsed = (Date.now() - startTime) / 1000;
                if (elapsed > 5 && elapsed < 30) {
                    updateStep(2, "Generating Cinematic Visuals...");
                    statusSubtext.innerText = "Creating documentary-style AI images for each scene.";
                } else if (elapsed > 30 && elapsed < 60) {
                    updateStep(3, "Recording Voiceover...");
                    statusSubtext.innerText = "Converting Hindi script to dramatic narration audio.";
                } else if (elapsed > 60) {
                    updateStep(4, "Assembling Final Video...");
                    statusSubtext.innerText = "Compositing visuals, audio, and captions into your documentary.";
                }
            }, 2000);

            const response = await fetch(`${API_BASE_URL}/generate`, {
                method: 'POST',
                body: formData
            });

            clearInterval(stepTimer);
            const data = await response.json();

            if (response.ok && data.status === "success") {
                clearInterval(timerInterval); // Stop timer
                updateStep(5, "Video Ready for Download!");

                setTimeout(() => {
                    statusOverlay.classList.add('hidden');
                    stepProgress.classList.add('hidden');
                    videoResult.classList.remove('hidden');
                    finalTimeValue.innerText = timerValue.innerText;

                    if (data.script_used) {
                        scriptBox.classList.remove('hidden');
                        scriptUsedText.innerText = data.script_used;
                    }

                    const topic = textarea.value.trim().substring(0, 30).replace(/[^a-z0-9]/gi, '_');
                    const fileName = `${topic || 'video'}.mp4`;

                    videoPreview.src = `${API_BASE_URL}${data.video_url}`;
                    downloadBtn.href = `${API_BASE_URL}${data.video_url}`;
                    downloadBtn.setAttribute('download', fileName);

                    if (uploadStatus) uploadStatus.classList.add('hidden');

                    // Auto-trigger the download
                    setTimeout(() => downloadBtn.click(), 500);
                }, 1000);
            } else {
                radarBox.classList.remove('active');
                stepProgress.classList.add('hidden');
                statusText.innerText = "Generation Failed";
                statusSubtext.innerText = data.message || "An error occurred. Please check your API keys.";
                statusSubtext.style.color = "#ef4444";
            }
        } else {
            // Standard Shorts flow
            const response = await fetch(`${API_BASE_URL}/generate`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.status === "success") {
                clearInterval(timerInterval); // Stop timer
                statusOverlay.classList.add('hidden');
                videoResult.classList.remove('hidden');
                finalTimeValue.innerText = timerValue.innerText;

                if (data.script_used) {
                    scriptBox.classList.remove('hidden');
                    scriptUsedText.innerText = data.script_used;
                }

                const topic = textarea.value.trim().substring(0, 30).replace(/[^a-z0-9]/gi, '_');
                const fileName = `${topic || 'video'}.mp4`;

                videoPreview.src = `${API_BASE_URL}${data.video_url}`;
                downloadBtn.href = `${API_BASE_URL}${data.video_url}`;
                downloadBtn.setAttribute('download', fileName);

                if (uploadStatus) uploadStatus.classList.add('hidden');

                // Auto-trigger the download
                setTimeout(() => downloadBtn.click(), 500);
            } else {
                radarBox.classList.remove('active');
                statusText.innerText = "Generation Failed";
                statusSubtext.innerText = data.message || "An error occurred. Please check your API keys.";
                statusSubtext.style.color = "#ef4444";
            }
        }
    } catch (error) {
        radarBox.classList.remove('active');
        stepProgress.classList.add('hidden');
        statusText.innerText = "Connection Error";
        statusSubtext.innerText = "Server is unreachable. Please try again.";
        statusSubtext.style.color = "#ef4444";
    } finally {
        clearInterval(timerInterval);
        btn.classList.remove('loading');
        btn.disabled = false;
        btn.querySelector('.btn-text').innerText = isDocumentary ? 'Build Documentary' : 'Build My Video';
    }
});

// ═══════════════════════════════════════════════════════════════════
//  YOUTUBE UPLOAD (local OAuth)
// ═══════════════════════════════════════════════════════════════════
if (uploadYoutubeBtn) {
    uploadYoutubeBtn.addEventListener('click', async () => {
        try {
            uploadYoutubeBtn.disabled = true;
            if (uploadStatus) {
                uploadStatus.classList.remove('hidden');
                uploadStatus.style.color = "";
                uploadStatus.innerText = "Starting YouTube upload (OAuth window may open)...";
            }

            // We always render to rendered_video.mp4 by default
            const title = (textarea?.value || "AI Documentary").trim().slice(0, 90) || "AI Documentary";
            const desc = "Generated with AI Video Creator";
            const tags = "shorts,ai,documentary";

            const fd = new FormData();
            fd.append("file_name", "rendered_video.mp4");
            fd.append("title", title);
            fd.append("description", desc);
            fd.append("tags", tags);
            fd.append("privacy_status", "public");

            const res = await fetch(`${API_BASE_URL}/upload-youtube`, { method: "POST", body: fd });
            const data = await res.json();
            if (res.ok && data.status === "success") {
                if (uploadStatus) {
                    uploadStatus.style.color = "#22c55e";
                    uploadStatus.innerText = `Uploaded! Video ID: ${data.video_id}`;
                }
            } else {
                if (uploadStatus) {
                    uploadStatus.style.color = "#ef4444";
                    uploadStatus.innerText = data.message || "Upload failed.";
                }
            }
        } catch (e) {
            if (uploadStatus) {
                uploadStatus.style.color = "#ef4444";
                uploadStatus.innerText = "Upload failed (connection error).";
            }
        } finally {
            uploadYoutubeBtn.disabled = false;
        }
    });
}
