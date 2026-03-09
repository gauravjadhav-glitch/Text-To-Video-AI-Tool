// ═══════════════════════════════════════════════════════════════════
//  SUGGEST IDEAS DROPDOWN
// ═══════════════════════════════════════════════════════════════════

// -- Toggle open/close --
const suggestToggleBtn = document.getElementById('suggest-toggle-btn');
const suggestDropdown = suggestToggleBtn ? suggestToggleBtn.closest('.suggest-dropdown') : null;

if (suggestToggleBtn && suggestDropdown) {
    suggestToggleBtn.addEventListener('click', () => {
        suggestDropdown.classList.toggle('open');
    });
}

// -- Pill selection (syncs to hidden #viral-niche input) --
const nichePills = document.querySelectorAll('.niche-pill');
const viralNiche = document.getElementById('viral-niche');

nichePills.forEach(pill => {
    pill.addEventListener('click', () => {
        nichePills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        if (viralNiche) viralNiche.value = pill.dataset.niche;
    });
});

// -- Fetch Ideas --
const viralBtn = document.getElementById('get-viral-btn');
const viralList = document.getElementById('viral-ideas-list');

if (viralBtn) {
    viralBtn.addEventListener('click', async () => {
        const niche = viralNiche ? viralNiche.value : 'mystery';
        viralBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading...';
        viralBtn.disabled = true;

        try {
            const response = await fetch(`${API_BASE_URL}/viral-ideas?niche=${niche}`);
            const data = await response.json();

            if (data.status === "success" && data.topics && data.topics.length) {
                viralList.innerHTML = '';
                data.topics.forEach(topic => {
                    const div = document.createElement('div');
                    div.className = 'idea-item';
                    div.textContent = topic;
                    div.addEventListener('click', () => {
                        // textarea may not be defined yet — guard it
                        const ta = document.getElementById('input_text');
                        if (ta) ta.value = topic;
                        // Collapse the dropdown after picking
                        if (suggestDropdown) suggestDropdown.classList.remove('open');
                    });
                    viralList.appendChild(div);
                });
            } else {
                viralList.innerHTML = '<p class="ideas-placeholder"><i class="fa-solid fa-triangle-exclamation"></i> No ideas returned. Try another category.</p>';
            }
        } catch (err) {
            console.error("Failed to fetch viral ideas:", err);
            viralList.innerHTML = '<p class="ideas-placeholder"><i class="fa-solid fa-wifi"></i> Connection error. Please try again.</p>';
        } finally {
            viralBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Fetch';
            viralBtn.disabled = false;
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
//  DYNAMIC PLACEHOLDER + VIRAL PREVIEW TOGGLE (Shorts mode)
// ═══════════════════════════════════════════════════════════════════
const viralPreviewCard = document.getElementById('viral-preview-card');

modeRadios.forEach(radio => {
    radio.addEventListener('change', (e) => {
        if (typeDoc.checked) return;  // Don't change if in documentary mode

        const val = e.target.value;

        // Show/hide viral preview card
        if (viralPreviewCard) {
            if (val === 'viral') {
                viralPreviewCard.classList.remove('hidden');
            } else {
                viralPreviewCard.classList.add('hidden');
            }
        }

        // Update placeholder and button label
        if (val === 'topic') {
            textarea.placeholder = "E.g., 5 mind-blowing facts about space in Marathi...";
            btn.querySelector('.btn-text').innerText = 'Build My Video';
        } else if (val === 'viral') {
            textarea.placeholder = "E.g., Jallianwala Bagh Massacre, 3 Bermuda Triangle secrets...";
            btn.querySelector('.btn-text').innerText = '🚀 Build Viral Short';
        } else {
            textarea.placeholder = "Paste your full 60s script here (Marathi supported)...";
            btn.querySelector('.btn-text').innerText = 'Build My Video';
        }
    });
});

// ═══════════════════════════════════════════════════════════════════
//  VIRAL SCRIPT PREVIEW — Generate Script button
// ═══════════════════════════════════════════════════════════════════
const previewViralBtn = document.getElementById('preview-viral-btn');
const viralPreviewBody = document.getElementById('viral-preview-body');

if (previewViralBtn && viralPreviewBody) {
    previewViralBtn.addEventListener('click', async () => {
        const topic = document.getElementById('input_text')?.value?.trim();
        if (!topic) {
            viralPreviewBody.innerHTML = '<p class="ideas-placeholder"><i class="fa-solid fa-triangle-exclamation"></i> Please enter a topic first.</p>';
            return;
        }

        const language = document.querySelector('input[name="language"]:checked')?.value || 'english';
        const duration = document.querySelector('input[name="duration"]:checked')?.value || 60;

        // Loading state
        previewViralBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating...';
        previewViralBtn.disabled = true;
        viralPreviewBody.innerHTML = '<p class="ideas-placeholder"><i class="fa-solid fa-spinner fa-spin"></i> AI is crafting your viral script…</p>';

        try {
            const fd = new FormData();
            fd.append('topic', topic);
            fd.append('duration', duration);
            fd.append('language', language);

            const res = await fetch(`${API_BASE_URL}/generate-viral-script`, { method: 'POST', body: fd });
            const data = await res.json();

            if (res.ok && data.status === 'success') {
                viralPreviewBody.innerHTML = renderViralPreview(data);
            } else {
                viralPreviewBody.innerHTML = `<p class="ideas-placeholder"><i class="fa-solid fa-triangle-exclamation"></i> ${data.message || 'Generation failed.'}</p>`;
            }
        } catch (err) {
            console.error('Viral preview error:', err);
            viralPreviewBody.innerHTML = '<p class="ideas-placeholder"><i class="fa-solid fa-wifi"></i> Connection error. Please try again.</p>';
        } finally {
            previewViralBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Generate Script';
            previewViralBtn.disabled = false;
        }
    });
}

/** Render the structured viral JSON into preview-card HTML */
function renderViralPreview(data) {
    let html = '';

    // Title
    if (data.title) {
        html += `<div class="vp-row">
            <span class="vp-label">📺 Title</span>
            <span class="vp-value" style="font-weight:600;color:var(--primary)">${escHtml(data.title)}</span>
        </div>`;
    }

    // Hook
    if (data.hook) {
        html += `<div class="vp-row">
            <span class="vp-label">⚡ Hook (first 3s)</span>
            <span class="vp-value">${escHtml(data.hook)}</span>
        </div>`;
    }

    // Scenes
    if (data.scenes && data.scenes.length) {
        html += `<div class="vp-label" style="margin-top:0.3rem">🎬 Scenes</div>`;
        data.scenes.forEach(s => {
            html += `<div class="vp-scene-block">
                <span class="vp-scene-num">Scene ${s.scene}</span>
                <span class="vp-scene-vo">${escHtml(s.voiceover || '')}</span>
                <span class="vp-scene-vis">🎨 ${escHtml(s.visual_prompt || '')}</span>
                <span class="vp-scene-cap">${escHtml(s.caption || '')}</span>
            </div>`;
        });
    }

    // Loop Ending
    if (data.loop_ending) {
        html += `<div class="vp-row">
            <span class="vp-label">🔁 Loop Ending</span>
            <span class="vp-value">${escHtml(data.loop_ending)}</span>
        </div>`;
    }

    // Hashtags
    if (data.hashtags && data.hashtags.length) {
        const tags = data.hashtags.map(t => `<span class="vp-tag">${escHtml(t)}</span>`).join('');
        html += `<div class="vp-row">
            <span class="vp-label"># Hashtags</span>
            <div class="vp-hashtags">${tags}</div>
        </div>`;
    }

    return html || '<p class="ideas-placeholder">No content returned.</p>';
}

function escHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

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
