// State Variables
const API_BASE = 'http://localhost:8000';
let currentPipeline = 'video'; // 'video' or 'posts'
let currentPlatform = 'instagram'; // 'instagram' or 'linkedin'
let selectedFile = null;
let currentJobId = null;
let pollInterval = null;
let activeAuthMode = 'login'; // 'login' or 'register'
let authToken = localStorage.getItem('access_token') || null;

// Initial Setup on Page Load
document.addEventListener('DOMContentLoaded', () => {
  checkAuthUser();
});

// Auth Functions
function checkAuthUser() {
  if (authToken) {
    document.getElementById('userGreeting').innerText = '👤 Authenticated';
    document.getElementById('userGreeting').style.display = 'inline-block';
    document.getElementById('authBtn').innerText = 'Logout';
    document.getElementById('authBtn').onclick = logoutUser;
    document.getElementById('registerBtn').style.display = 'none';
  } else {
    document.getElementById('userGreeting').style.display = 'none';
    document.getElementById('authBtn').innerText = 'Login';
    document.getElementById('authBtn').onclick = () => openAuthModal('login');
    document.getElementById('registerBtn').style.display = 'inline-flex';
  }
}

function openAuthModal(mode) {
  activeAuthMode = mode;
  const modal = document.getElementById('authModal');
  const title = document.getElementById('modalTitle');
  const sub = document.getElementById('modalSub');
  const emailGroup = document.getElementById('emailGroup');
  const submitBtn = document.getElementById('authSubmitBtn');

  if (mode === 'login') {
    title.innerText = 'Login to PostEazy';
    sub.innerText = 'Sign in to access your content generation engine.';
    emailGroup.style.display = 'none';
    submitBtn.innerText = 'Sign In';
  } else {
    title.innerText = 'Create your Account';
    sub.innerText = 'Register to start converting documents into content.';
    emailGroup.style.display = 'block';
    submitBtn.innerText = 'Register';
  }

  modal.classList.add('active');
}

function closeAuthModal() {
  document.getElementById('authModal').classList.remove('active');
}

async function handleAuthSubmit(e) {
  e.preventDefault();
  const username = document.getElementById('authUsername').value;
  const password = document.getElementById('authPassword').value;
  const email = document.getElementById('authEmail').value;

  try {
    if (activeAuthMode === 'register') {
      const res = await fetch(`${API_BASE}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Registration failed');
      }
      showToast('✅ Account registered successfully! Logging in...');
      openAuthModal('login');
      return;
    } else {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Login failed');
      }

      const tokenData = await res.json();
      authToken = tokenData.access_token;
      localStorage.setItem('access_token', authToken);
      closeAuthModal();
      checkAuthUser();
      showToast('🎉 Authenticated successfully!');
    }
  } catch (err) {
    showToast(`❌ Auth Error: ${err.message}`);
  }
}

function logoutUser() {
  localStorage.removeItem('access_token');
  authToken = null;
  checkAuthUser();
  showToast('Logged out');
}

// Pipeline & Platform Switchers
function selectPipeline(pipeline) {
  currentPipeline = pipeline;
  document.getElementById('tabVideo').classList.toggle('active', pipeline === 'video');
  document.getElementById('tabPosts').classList.toggle('active', pipeline === 'posts');

  const kineticBtn = document.getElementById('btnRenderKinetic');
  if (pipeline === 'video') {
    kineticBtn.innerText = 'Render Kinetic Video 🎬';
  } else {
    kineticBtn.innerText = 'Render Static Posts Carousel 🖼️';
  }

  showToast(`Switched to ${pipeline === 'video' ? 'Pipeline B (Faceless Video)' : 'Pipeline A (Static Posts)'}`);
}

function selectPlatform(platform) {
  currentPlatform = platform;
  document.getElementById('platInstagram').classList.toggle('selected', platform === 'instagram');
  document.getElementById('platLinkedin').classList.toggle('selected', platform === 'linkedin');
  showToast(`Platform preset: ${platform.toUpperCase()}`);
}

// File Handlers
function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file) setFile(file);
}

function setFile(file) {
  selectedFile = file;
  document.getElementById('fileName').innerText = `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
  document.getElementById('fileInfo').style.display = 'flex';
  document.getElementById('dropzone').style.borderColor = '#34d399';
  showToast(`Loaded document: ${file.name}`);
}

function clearFile(event) {
  event.stopPropagation();
  selectedFile = null;
  document.getElementById('fileInput').value = '';
  document.getElementById('fileInfo').style.display = 'none';
  document.getElementById('dropzone').style.borderColor = 'rgba(255, 255, 255, 0.2)';
}

// Drag & Drop
const dropzone = document.getElementById('dropzone');
dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropzone.classList.remove('dragover');
  if (e.dataTransfer.files.length > 0) setFile(e.dataTransfer.files[0]);
});

// Step 1: Review Script JSON
async function generateScriptReview() {
  if (!selectedFile) {
    showToast('⚠️ Upload a document first!');
    return;
  }

  showToast('🔍 Distilling document into script...');
  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('platform', currentPlatform);

  const endpoint = currentPipeline === 'video' ? `${API_BASE}/api/video/scripts` : `${API_BASE}/api/posts/scripts`;

  try {
    const res = await fetch(endpoint, { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Script generation failed');
    }

    const scriptData = await res.json();
    document.getElementById('scriptEditor').value = JSON.stringify(scriptData, null, 2);
    showToast('✅ Script generated! Review below.');

    if (currentPipeline === 'posts') {
      renderStaticCarouselPreview(scriptData);
    }
  } catch (error) {
    showToast(`❌ Error: ${error.message}`);
  }
}

// Step 2: Main Render Action
async function startKineticRender() {
  if (!selectedFile) {
    showToast('⚠️ Upload a document first!');
    return;
  }

  const duration = document.getElementById('targetDuration').value || 60;
  const formatPreset = document.getElementById('formatPreset').value || 'shorts';

  const statusBanner = document.getElementById('statusBanner');
  statusBanner.style.display = 'block';
  statusBanner.innerText = `Rendering ${formatPreset} content (${duration}s)...`;

  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('platform', currentPlatform);
  formData.append('duration_seconds', duration);

  const endpoint = currentPipeline === 'video' ? `${API_BASE}/api/video/jobs` : `${API_BASE}/api/posts/jobs`;

  try {
    const res = await fetch(endpoint, { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Job creation failed');
    }

    const jobData = await res.json();
    currentJobId = jobData.job_id;

    document.getElementById('progressBox').style.display = 'block';
    document.getElementById('jobStatusBadge').style.display = 'inline-block';

    showToast(`🚀 Render Job '${currentJobId}' queued!`);
    startPollingJob(currentJobId);

  } catch (error) {
    statusBanner.innerText = `❌ Error: ${error.message}`;
    showToast(`❌ Render Error: ${error.message}`);
  }
}

// Job Polling Loop
function startPollingJob(jobId) {
  if (pollInterval) clearInterval(pollInterval);

  pollInterval = setInterval(async () => {
    const statusEndpoint = currentPipeline === 'video'
      ? `${API_BASE}/api/video/jobs/${jobId}`
      : `${API_BASE}/api/posts/jobs/${jobId}`;

    try {
      const res = await fetch(statusEndpoint);
      if (!res.ok) return;

      const job = await res.json();
      updateJobUI(job);

      if (job.status === 'done' || job.status === 'failed') {
        clearInterval(pollInterval);
        if (job.status === 'done') {
          showToast('🎉 Content rendered successfully!');
          renderFinalOutputs(job);
        } else {
          showToast(`❌ Job Failed: ${job.error || 'Unknown error'}`);
        }
      }
    } catch (e) {
      console.error(e);
    }
  }, 2000);
}

function updateJobUI(job) {
  const badge = document.getElementById('jobStatusBadge');
  badge.className = `status-badge status-${job.status}`;
  badge.innerText = job.status.toUpperCase();

  const statusBanner = document.getElementById('statusBanner');
  if (job.status === 'done') {
    statusBanner.style.display = 'block';
    statusBanner.innerText = 'Rendering complete! Loading playback...';
  } else if (job.status === 'running') {
    statusBanner.style.display = 'block';
    statusBanner.innerText = `Stage: ${job.stage} (${job.progress}%)`;
  }

  document.getElementById('stageLabel').innerText = job.stage || 'Processing...';
  document.getElementById('progressPercent').innerText = `${job.progress || 0}%`;
  document.getElementById('progressFill').style.width = `${job.progress || 0}%`;

  if (job.script) {
    document.getElementById('scriptEditor').value = JSON.stringify(job.script, null, 2);
  }
}

// Carousel Slide Renderer
let activeSlideIndex = 0;
let carouselSlides = [];

function renderStaticCarouselPreview(scriptData) {
  carouselSlides = scriptData.slides || [];
  activeSlideIndex = 0;
  displayActiveSlide();
}

function displayActiveSlide() {
  if (!carouselSlides || carouselSlides.length === 0) return;

  const slide = carouselSlides[activeSlideIndex];
  const previewBox = document.getElementById('previewBox');

  previewBox.innerHTML = `
    <div class="carousel-preview">
      <div class="carousel-slide-card">
        <div>
          <div class="slide-header">${currentPlatform.toUpperCase()} CAROUSEL • SLIDE ${activeSlideIndex + 1} OF ${carouselSlides.length}</div>
          <div class="slide-heading">${slide.heading}</div>
          <div class="slide-body">${slide.body}</div>
        </div>
        ${slide.stat ? `<div class="slide-stat">${slide.stat}</div>` : ''}
        <div style="font-size: 11px; color: var(--accent-cyan); text-align: right;">SWIPE ➔</div>
      </div>
      <div class="carousel-controls">
        <button class="btn btn-ghost" style="padding: 8px 14px;" onclick="prevSlide()">◄ Prev</button>
        <span style="font-size: 13px; color: var(--text-muted);">${activeSlideIndex + 1} / ${carouselSlides.length}</span>
        <button class="btn btn-ghost" style="padding: 8px 14px;" onclick="nextSlide()">Next ►</button>
      </div>
    </div>
  `;
}

function prevSlide() {
  if (activeSlideIndex > 0) { activeSlideIndex--; displayActiveSlide(); }
}

function nextSlide() {
  if (activeSlideIndex < carouselSlides.length - 1) { activeSlideIndex++; displayActiveSlide(); }
}

// Final Outputs Player
function renderFinalOutputs(job) {
  const previewBox = document.getElementById('previewBox');

  if (currentPipeline === 'video') {
    previewBox.innerHTML = `
      <div style="width: 100%; text-align: center; padding: 24px;">
        <video controls autoplay style="max-height: 440px; border-radius: 12px; box-shadow: 0 12px 32px rgba(0,0,0,0.6);">
          <source src="${API_BASE}/api/video/jobs/${job.job_id}/download" type="video/mp4">
          Your browser does not support HTML5 video playback.
        </video>
        <div style="margin-top: 20px;">
          <a href="${API_BASE}/api/video/jobs/${job.job_id}/download" download class="btn btn-gradient" style="display: inline-flex;">
            ⬇️ Download 9:16 MP4 Deliverable
          </a>
        </div>
      </div>
    `;
  } else {
    previewBox.innerHTML = `
      <div style="width: 100%; text-align: center; padding: 24px;">
        <div style="font-size: 44px; margin-bottom: 12px;">🖼️</div>
        <h3 style="margin-bottom: 12px;">Static Carousel Deck Ready!</h3>
        <p style="color: var(--text-muted); margin-bottom: 20px;">All high-resolution PNG slides generated successfully.</p>
        <a href="${API_BASE}/api/posts/jobs/${job.job_id}/download" download class="btn btn-gradient" style="display: inline-flex;">
          📦 Download Carousel Deck ZIP / PDF
        </a>
      </div>
    `;
  }
}

function showToast(msg) {
  const toast = document.getElementById('toast');
  toast.innerText = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3500);
}
