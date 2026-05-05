/* ===========================
   EduClips — Frontend App
   =========================== */

const API_BASE = window.location.origin;

let currentJobId = null;
let pollInterval = null;
let selectedFile = null;

// ===== DOM References =====
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const generateBtn = document.getElementById('generate-btn');
const uploadSection = document.getElementById('upload-section');
const progressSection = document.getElementById('progress-section');
const errorSection = document.getElementById('error-section');
const resultsSection = document.getElementById('results-section');
const progressBar = document.getElementById('progress-bar');
const progressMessage = document.getElementById('progress-message');
const clipsGrid = document.getElementById('clips-grid');

// ===== File Selection =====
fileInput.addEventListener('change', (e) => handleFile(e.target.files[0]));

dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('keydown', (e) => { if (e.key === 'Enter') fileInput.click(); });

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

function handleFile(file) {
  if (!file) return;

  const allowedTypes = ['video/mp4', 'video/mpeg', 'video/quicktime', 'video/x-msvideo', 'video/webm'];
  if (!allowedTypes.includes(file.type)) {
    alert('Please upload a video file (MP4, MOV, AVI, or WEBM).');
    return;
  }

  const maxMB = 500;
  if (file.size > maxMB * 1024 * 1024) {
    alert(`File too large. Maximum size is ${maxMB}MB.`);
    return;
  }

  selectedFile = file;

  // Update UI
  document.getElementById('drop-content').classList.add('hidden');
  document.getElementById('drop-preview').classList.remove('hidden');
  document.getElementById('preview-filename').textContent = file.name;
  document.getElementById('preview-filesize').textContent = formatBytes(file.size);
  dropZone.classList.add('has-file');

  generateBtn.disabled = false;
}

// ===== Generate Button =====
generateBtn.addEventListener('click', async () => {
  if (!selectedFile) return;

  const formData = new FormData();
  formData.append('file', selectedFile);

  showSection('progress');
  generateBtn.disabled = true;
  resetSteps();

  try {
    const res = await fetch(`${API_BASE}/api/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Upload failed');
    }

    const data = await res.json();
    currentJobId = data.job_id;
    startPolling(currentJobId);

  } catch (err) {
    showError(err.message || 'Failed to upload video. Please try again.');
  }
});

// ===== Polling =====
function startPolling(jobId) {
  pollInterval = setInterval(() => pollStatus(jobId), 2500);
}

async function pollStatus(jobId) {
  try {
    const res = await fetch(`${API_BASE}/api/status/${jobId}`);
    if (!res.ok) return;

    const job = await res.json();
    updateProgress(job);

    if (job.status === 'completed') {
      clearInterval(pollInterval);
      showResults(job.clips);
    } else if (job.status === 'failed') {
      clearInterval(pollInterval);
      showError(job.error || 'Processing failed. Please try a different video.');
    }
  } catch (err) {
    console.error('Polling error:', err);
  }
}

function updateProgress(job) {
  const pct = job.progress || 0;
  progressBar.style.width = `${pct}%`;
  progressMessage.textContent = job.message || 'Processing...';

  // Update step indicators based on progress
  if (pct >= 10) markStep(1, pct >= 25 ? 'done' : 'active');
  if (pct >= 25) markStep(2, pct >= 45 ? 'done' : 'active');
  if (pct >= 45) markStep(3, pct >= 65 ? 'done' : 'active');
  if (pct >= 65) markStep(4, pct >= 85 ? 'done' : 'active');
  if (pct >= 85) markStep(5, pct >= 100 ? 'done' : 'active');
}

function markStep(num, state) {
  const step = document.getElementById(`step-${num}`);
  const status = document.getElementById(`step-${num}-status`);
  step.className = `step ${state}`;
  status.textContent = state === 'done' ? '✅' : state === 'active' ? '⚙️' : '⏳';
}

function resetSteps() {
  for (let i = 1; i <= 5; i++) {
    document.getElementById(`step-${i}`).className = 'step';
    document.getElementById(`step-${i}-status`).textContent = '⏳';
  }
  progressBar.style.width = '0%';
}

// ===== Results Rendering =====
function showResults(clips) {
  showSection('results');

  document.getElementById('results-subtitle').textContent =
    `Generated ${clips.length} clip${clips.length !== 1 ? 's' : ''} from your video`;

  clipsGrid.innerHTML = '';
  clips.forEach((clip, i) => {
    clipsGrid.appendChild(buildClipCard(clip, i + 1));
  });
}

function buildClipCard(clip, num) {
  const card = document.createElement('div');
  card.className = 'clip-card';

  const duration = clip.duration ? `${Math.round(clip.duration)}s` : '';
  const hPath = clip.horizontal_path ? `/${clip.horizontal_path}` : '';
  const vPath = clip.vertical_path ? `/${clip.vertical_path}` : '';
  const thumbPath = clip.thumbnail_path ? `/${clip.thumbnail_path}` : '';

  card.innerHTML = `
    <div class="clip-header">
      <div class="clip-number">${num}</div>
      <div class="clip-title">${escHtml(clip.title || `Clip ${num}`)}</div>
      ${duration ? `<span class="clip-duration">⏱ ${duration}</span>` : ''}
    </div>

    <div class="clip-body">
      <!-- Video Preview -->
      <div class="video-container">
        <div class="video-label">Preview (Horizontal 16:9)</div>
        <div class="video-wrapper">
          <video controls preload="metadata" ${hPath ? `src="${hPath}"` : ''}>
            Your browser does not support video.
          </video>
        </div>
      </div>

      <!-- Clip Meta -->
      <div class="clip-meta">
        <div class="meta-block">
          <div class="meta-label">Description</div>
          <div class="meta-value">${escHtml(clip.description || '')}</div>
        </div>

        ${clip.hook_score !== undefined ? `
        <div class="meta-block">
          <div class="meta-label">AI Scores</div>
          <div class="scores">
            <span class="score-pill score-hook">🎣 Hook: ${clip.hook_score}/10</span>
            <span class="score-pill score-clarity">💡 Clarity: ${clip.clarity_score}/10</span>
            <span class="score-pill score-engage">⚡ Engage: ${clip.engagement_score}/10</span>
          </div>
        </div>` : ''}

        ${clip.hashtags ? `
        <div class="meta-block">
          <div class="meta-label">Hashtags</div>
          <div class="hashtags">${escHtml(clip.hashtags)}</div>
        </div>` : ''}

        <div class="clip-actions">
          ${hPath ? `<a href="${hPath}" download class="btn btn-primary btn-sm">⬇ Horizontal (16:9)</a>` : ''}
          ${vPath ? `<a href="${vPath}" download class="btn btn-secondary btn-sm">⬇ Vertical (9:16)</a>` : ''}
        </div>
      </div>
    </div>

    <!-- Thumbnail Concept -->
    ${clip.thumbnail_text ? `
    <div class="thumbnail-container">
      <div class="thumbnail-label">Thumbnail Concept</div>
      <div class="thumbnail-box">
        ${thumbPath
          ? `<img src="${thumbPath}" alt="Thumbnail for clip ${num}" loading="lazy" />`
          : `<div class="thumbnail-placeholder">
               <div>📸 Screenshot from clip</div>
               <div class="thumb-text-overlay">${escHtml(clip.thumbnail_text)}</div>
             </div>`
        }
      </div>
    </div>` : ''}
  `;

  return card;
}

// ===== Section Navigation =====
function showSection(name) {
  uploadSection.classList.add('hidden');
  progressSection.classList.add('hidden');
  errorSection.classList.add('hidden');
  resultsSection.classList.add('hidden');

  if (name === 'upload') uploadSection.classList.remove('hidden');
  if (name === 'progress') progressSection.classList.remove('hidden');
  if (name === 'error') errorSection.classList.remove('hidden');
  if (name === 'results') resultsSection.classList.remove('hidden');
}

function showError(message) {
  showSection('error');
  document.getElementById('error-message').textContent = message;
}

function resetApp() {
  if (pollInterval) clearInterval(pollInterval);
  currentJobId = null;
  selectedFile = null;

  // Reset file input and drop zone
  fileInput.value = '';
  document.getElementById('drop-content').classList.remove('hidden');
  document.getElementById('drop-preview').classList.add('hidden');
  dropZone.classList.remove('has-file', 'dragover');
  generateBtn.disabled = true;

  showSection('upload');
}

// ===== Utilities =====
function formatBytes(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
