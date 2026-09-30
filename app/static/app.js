// State Variables
let currentPipeline = 'video'; // 'video' or 'posts'
let currentPlatform = 'instagram'; // 'instagram' or 'linkedin'
let selectedFile = null;
let currentJobId = null;
let pollInterval = null;

// Pipeline Selection
function selectPipeline(pipeline) {
  currentPipeline = pipeline;
  document.getElementById('tabVideo').classList.toggle('active', pipeline === 'video');
  document.getElementById('tabPosts').classList.toggle('active', pipeline === 'posts');
  showToast(`Switched to ${pipeline === 'video' ? 'Pipeline B (Faceless Video)' : 'Pipeline A (Static Posts)'}`);
}

// Platform Selection
function selectPlatform(platform) {
  currentPlatform = platform;
  document.getElementById('platInstagram').classList.toggle('selected', platform === 'instagram');
  document.getElementById('platLinkedin').classList.toggle('selected', platform === 'linkedin');
  showToast(`Platform preset set to ${platform.toUpperCase()}`);
}

// File Selection & Drag-and-Drop Handlers
function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file) {
    setFile(file);
  }
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

// Drag & Drop Listeners
const dropzone = document.getElementById('dropzone');
dropzone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropzone.classList.add('dragover');
});
dropzone.addEventListener('dragleave', () => {
  dropzone.classList.remove('dragover');
});
dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropzone.classList.remove('dragover');
  if (e.dataTransfer.files.length > 0) {
    setFile(e.dataTransfer.files[0]);
  }
});

// Step 1: Generate & Review Script
async function generateScriptReview() {
  if (!selectedFile) {
    showToast('⚠️ Please upload a document first!');
    return;
  }

  showToast('🔍 Analyzing document & generating script...');
  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('platform', currentPlatform);

  const endpoint = currentPipeline === 'video' ? '/api/video/scripts' : '/api/posts/scripts';

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Script generation failed');
    }

    const scriptData = await res.json();
    document.getElementById('scriptEditor').value = JSON.stringify(scriptData, null, 2);
    showToast('✅ Script generated! Review and edit JSON below.');

    // Render initial preview from script
    if (currentPipeline === 'posts') {
      renderStaticCarouselPreview(scriptData);
    }
  } catch (error) {
    showToast(`❌ Error: ${error.message}`);
  }
}

// Step 2: Render Content Job
async function startGenerationJob() {
  if (!selectedFile) {
    showToast('⚠️ Please upload a document first!');
    return;
  }

  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('platform', currentPlatform);

  const endpoint = currentPipeline === 'video' ? '/api/video/jobs' : '/api/posts/jobs';

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Job initialization failed');
    }

    const jobData = await res.json();
    currentJobId = jobData.job_id;
    
    // Show Progress Bar
    document.getElementById('progressBox').style.display = 'block';
    document.getElementById('jobStatusBadge').style.display = 'inline-block';
    
    showToast(`🚀 Render Job '${currentJobId}' queued!`);
    startPollingJob(currentJobId);

  } catch (error) {
    showToast(`❌ Job Error: ${error.message}`);
  }
}

// Polling Job Status
function startPollingJob(jobId) {
  if (pollInterval) clearInterval(pollInterval);

  pollInterval = setInterval(async () => {
    const statusEndpoint = currentPipeline === 'video' 
      ? `/api/video/jobs/${jobId}` 
      : `/api/posts/jobs/${jobId}`;

    try {
      const res = await fetch(statusEndpoint);
      if (!res.ok) return;

      const job = await res.json();
      updateJobUI(job);

      if (job.status === 'done' || job.status === 'failed') {
        clearInterval(pollInterval);
        if (job.status === 'done') {
          showToast('🎉 Rendering completed successfully!');
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

// Render Kinetic Video Action Handler
async function startKineticRender() {
  if (!selectedFile) {
    showToast('⚠️ Please upload a document first!');
    return;
  }

  const duration = document.getElementById('targetDuration').value || 60;
  const formatPreset = document.getElementById('formatPreset').value || 'shorts';
  
  const statusBanner = document.getElementById('statusBanner');
  statusBanner.style.display = 'block';
  statusBanner.innerText = `Rendering ${formatPreset} kinetic video (${duration}s)...`;

  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('platform', currentPlatform);
  formData.append('duration_seconds', duration);

  const endpoint = currentPipeline === 'video' ? '/api/video/jobs' : '/api/posts/jobs';

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Job initialization failed');
    }

    const jobData = await res.json();
    currentJobId = jobData.job_id;
    
    document.getElementById('progressBox').style.display = 'block';
    document.getElementById('jobStatusBadge').style.display = 'inline-block';
    
    showToast(`🎬 Kinetic Render Job '${currentJobId}' started!`);
    startPollingJob(currentJobId);

  } catch (error) {
    statusBanner.innerText = `❌ Error: ${error.message}`;
    showToast(`❌ Render Error: ${error.message}`);
  }
}

// UI State Updater
function updateJobUI(job) {
  const badge = document.getElementById('jobStatusBadge');
  badge.className = `status-badge status-${job.status}`;
  badge.innerText = job.status.toUpperCase();

  const statusBanner = document.getElementById('statusBanner');
  if (job.status === 'done') {
    statusBanner.style.display = 'block';
    statusBanner.innerText = 'Rendering complete! Loading video playback...';
  } else if (job.status === 'running') {
    statusBanner.style.display = 'block';
    statusBanner.innerText = `Stage: ${job.stage} (${job.progress}%)`;
  }

  document.getElementById('stageLabel').innerText = job.stage || 'Processing...';
  document.getElementById('progressPercent').innerText = `${job.progress || 0}%`;
  document.getElementById('progressFill').style.width = `${job.progress || 0}%`;
}

// Render Static Carousel Card Preview
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
        <div style="font-size: 11px; color: var(--accent-blue); text-align: right;">SWIPE ➔</div>
      </div>
      <div class="carousel-controls">
        <button class="btn-icon" onclick="prevSlide()">◄</button>
        <span style="font-size: 13px; color: var(--text-muted);">${activeSlideIndex + 1} / ${carouselSlides.length}</span>
        <button class="btn-icon" onclick="nextSlide()">►</button>
      </div>
    </div>
  `;
}

function prevSlide() {
  if (activeSlideIndex > 0) {
    activeSlideIndex--;
    displayActiveSlide();
  }
}

function nextSlide() {
  if (activeSlideIndex < carouselSlides.length - 1) {
    activeSlideIndex++;
    displayActiveSlide();
  }
}

// Render Final Outputs (Video or Static Posts)
function renderFinalOutputs(job) {
  const previewBox = document.getElementById('previewBox');

  if (currentPipeline === 'video') {
    previewBox.innerHTML = `
      <div style="width: 100%; text-align: center; padding: 20px;">
        <video controls autoplay style="max-height: 440px; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.6);">
          <source src="/api/video/jobs/${job.job_id}/download" type="video/mp4">
          Your browser does not support the video tag.
        </video>
        <div style="margin-top: 16px;">
          <a href="/api/video/jobs/${job.job_id}/download" download class="btn-primary" style="display: inline-flex; width: auto; padding: 10px 24px;">
            ⬇️ Download 9:16 MP4 Video
          </a>
        </div>
      </div>
    `;
  } else {
    previewBox.innerHTML = `
      <div style="width: 100%; text-align: center; padding: 20px;">
        <div style="font-size: 40px; margin-bottom: 12px;">🖼️</div>
        <h3 style="margin-bottom: 12px;">Carousel Render Complete!</h3>
        <p style="color: var(--text-muted); margin-bottom: 20px;">All high-resolution PNG slides generated successfully.</p>
        <a href="/api/posts/jobs/${job.job_id}/download" download class="btn-primary" style="display: inline-flex; width: auto; padding: 10px 24px;">
          📦 Download Slides ZIP / PDF
        </a>
      </div>
    `;
  }
}

// Toast Notifications
function showToast(message) {
  const toast = document.getElementById('toast');
  toast.innerText = message;
  toast.classList.add('show');
  setTimeout(() => {
    toast.classList.remove('show');
  }, 3500);
}
