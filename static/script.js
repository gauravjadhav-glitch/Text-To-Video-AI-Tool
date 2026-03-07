// Select Elements
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
const timerContainer = document.getElementById('timer-container');
const timerValue = document.getElementById('timer-value');
const scriptBox = document.getElementById('final-script-display');
const scriptUsedText = document.getElementById('script-used-text');
const finalTimeValue = document.getElementById('final-time-value');
const API_BASE_URL = "https://text-to-video-ai-tool.onrender.com";

// 1. Dynamic Placeholder for Textarea
modeRadios.forEach(radio => {
    radio.addEventListener('change', (e) => {
        if (e.target.value === 'topic') {
            textarea.placeholder = "E.g., 5 mind-blowing facts about space in Marathi...";
        } else {
            textarea.placeholder = "Paste your full 60s script here (Marathi supported)...";
        }
    });
});

// 2. Handle mutually exclusive checkboxes
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

// 2. Form Submission
form.addEventListener('submit', async function (e) {
    e.preventDefault();

    // Reset UI State
    btn.classList.add('loading');
    btn.disabled = true;
    btn.querySelector('.btn-text').innerText = 'Processing...';

    videoResult.classList.add('hidden');
    scriptBox.classList.add('hidden');
    statusOverlay.classList.remove('hidden');
    radarBox.classList.add('active');
    timerContainer.classList.remove('hidden');

    statusText.innerText = "Processing Idea...";
    statusSubtext.innerText = "Generating script, voiceover, and visual content. Please hold on.";

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
    const duration = document.querySelector('input[name="duration"]:checked').value;
    const mode = document.querySelector('input[name="mode"]:checked').value;
    const language = document.querySelector('input[name="language"]:checked').value;

    const useAI = aiCheckbox.checked;
    const useStock = stockCheckbox.checked;

    const formData = new FormData();
    formData.append('input_text', textarea.value);
    formData.append('mode', mode);
    formData.append('duration', duration);
    formData.append('language', language);
    formData.append('use_ai_images', useAI);
    formData.append('use_stock_images', useStock);

    try {
        const response = await fetch(`${API_BASE_URL}/generate`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok && data.status === "success") {
            statusOverlay.classList.add('hidden');
            videoResult.classList.remove('hidden');

            // Set final generation time
            finalTimeValue.innerText = timerValue.innerText;

            // Show final script if it was generated
            if (data.script_used) {
                scriptBox.classList.remove('hidden');
                scriptUsedText.innerText = data.script_used;
            }

            videoPreview.src = `${API_BASE_URL}${data.video_url}`;
            downloadBtn.href = `${API_BASE_URL}${data.video_url}`;
        } else {
            radarBox.classList.remove('active');
            statusText.innerText = "Generation Failed";
            statusSubtext.innerText = data.message || "An error occurred. Please check your API keys.";
            statusSubtext.style.color = "#ef4444";
        }
    } catch (error) {
        radarBox.classList.remove('active');
        statusText.innerText = "Connection Error";
        statusSubtext.innerText = "Server is unreachable. Please try again.";
        statusSubtext.style.color = "#ef4444";
    } finally {
        clearInterval(timerInterval);
        btn.classList.remove('loading');
        btn.disabled = false;
        btn.querySelector('.btn-text').innerText = 'Build My Short';
    }
});
