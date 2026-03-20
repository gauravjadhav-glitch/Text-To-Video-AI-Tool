// Production URL (Update this with your actual Render URL if using separate deployment)
const RENDER_BACKEND_URL = "https://text-to-video-ai-tool.onrender.com";

const API_BASE_URL = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://localhost:8000"
    : (window.location.origin.includes("vercel.app") ? RENDER_BACKEND_URL : window.location.origin);

console.log("API_BASE_URL calculated as:", API_BASE_URL);

document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM fully loaded and parsed");

    // ═══════════════════════════════════════════════════════════════════
    //  SELECT ELEMENTS
    // ═══════════════════════════════════════════════════════════════════
    const form = document.getElementById('generate-form');
    const btn = document.getElementById('generate-btn');
    const textarea = document.getElementById('input_text');
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

    const finalTimeValue = document.getElementById('final-time-value');
    const instructionText = document.getElementById('instruction-text');

    if (!form) {
        console.error("Form NOT found: generate-form");
        return;
    }
    console.log("Form found successfully");

    // ═══════════════════════════════════════════════════════════════════
    //  INPUT TYPE SWITCH: Simple vs Direct
    // ═══════════════════════════════════════════════════════════════════
    document.querySelectorAll('input[name="input_type"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            const isDirect = e.target.value === 'direct';

            if (isDirect) {
                textarea.placeholder = "Paste your full JSON Director's script here...";
                instructionText.innerHTML = "The AI will exactly follow the provided structured <strong>Director's Vision</strong> script.";
            } else {
                textarea.placeholder = "E.g., A rainy night in a futuristic city with flying cars...";
                instructionText.innerHTML = "The AI will expand your simple prompt into a heavily detailed cinematic <strong>Director's Vision</strong>.";
            }
        });
    });

    // ═══════════════════════════════════════════════════════════════════
    //  FORM SUBMISSION
    // ═══════════════════════════════════════════════════════════════════
    form.addEventListener('submit', async function (e) {
        console.log("Form submit event triggered");
        e.preventDefault();

        // Reset UI State
        btn.classList.add('loading');
        btn.disabled = true;
        btn.querySelector('.btn-text').innerText = 'Processing...';

        videoResult.classList.add('hidden');

        statusOverlay.classList.remove('hidden');
        radarBox.classList.add('active');
        timerContainer.classList.remove('hidden');

        statusText.innerText = "Processing Idea...";
        statusSubtext.innerText = "Generating structural script and compiling background video. Please hold on.";

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
        const formData = new FormData();
        formData.append('input_text', textarea.value);
        
        // Default duration is 30 unless set
        const durationBtn = document.querySelector('input[name="duration"]:checked');
        const duration = durationBtn ? durationBtn.value : '30';
        formData.append('duration', duration);
        
        const inputTypeBtn = document.querySelector('input[name="input_type"]:checked');
        const inputType = inputTypeBtn ? inputTypeBtn.value : 'simple';
        formData.append('input_type', inputType);

        try {
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
        } catch (error) {
            console.error("Fetch error:", error);
            radarBox.classList.remove('active');
            statusText.innerText = "Connection Error";
            statusSubtext.innerText = "Server is unreachable. Please try again.";
            statusSubtext.style.color = "#ef4444";
        } finally {
            clearInterval(timerInterval);
            btn.classList.remove('loading');
            btn.disabled = false;
            btn.querySelector('.btn-text').innerText = 'Build My Video';
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
});
