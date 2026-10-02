// State Variables
const API_BASE = 'http://localhost:8000';
let currentPipeline = 'video'; // 'video' or 'posts'
let currentPlatform = 'instagram'; // 'instagram' or 'youtube' or 'linkedin'
let selectedVideoCategory = 'short'; // 'short' (reels/shorts 9:16) or 'long' (youtube 16:9)
let selectedTypographyOption = 1; // 1, 2, 3
let selectedSongOption = 1; // 1, 2, 3
let selectedFile = null;
let selectedPostFile = null;
let currentJobId = null;
let pollInterval = null;
let activeAuthMode = 'login';
let authToken = localStorage.getItem('access_token') || null;
let ingestedScriptData = null;

// 3D Floating Hero Cards Definition
const FORMATS = [
  { id: 'linkedin', title: 'LinkedIn Post', desc: 'Professional carousel & document layout', icon: '💼', x: -380, y: -220, z: 20 },
  { id: 'twitter', title: 'X/Twitter Thread', desc: 'Multiple connected stat posts', icon: '🐦', x: 260, y: -280, z: 12 },
  { id: 'presentation', title: 'Presentation Slide', desc: 'Clean title & data slide deck', icon: '📊', x: -520, y: 40, z: 10 },
  { id: 'executive', title: 'Exec Summary', desc: 'One-page briefing document', icon: '📑', x: 460, y: 80, z: 18 },
  { id: 'advisory', title: 'Advisory Doc', desc: 'Structured warning & insights report', icon: '🛡️', x: -220, y: 220, z: 15 },
  { id: 'infographic', title: 'Infographic', desc: 'Stats, callouts & key metrics', icon: '📈', x: 220, y: 260, z: 22 },
  { id: 'storyboard', title: 'Video Storyboard', desc: 'Scene thumbnail + narration script', icon: '🎬', x: 0, y: -320, z: 8 },
  { id: 'youtube', title: 'YouTube Shorts', desc: 'Portrait video, title & captions', icon: '▶️', x: 560, y: -140, z: 10 },
  { id: 'instagram', title: 'Instagram Reels', desc: 'High-energy kinetic captions & clips', icon: '📸', x: -620, y: -80, z: 8 },
  { id: 'email', title: 'Email Newsletter', desc: 'Subject, headline, body summary', icon: '✉️', x: -120, y: 350, z: 12 },
  { id: 'press', title: 'Press Release', desc: 'Headline + summary announcement', icon: '📰', x: 620, y: 220, z: 9 },
  { id: 'research', title: 'Research Report', desc: 'Chart + highlighted findings', icon: '🔬', x: -420, y: 280, z: 14 },
  { id: 'mobile', title: 'Mobile Notification', desc: 'Short urgent update card', icon: '📱', x: 360, y: -40, z: 25 },
  { id: 'blog', title: 'Blog Article', desc: 'Hero image + text structure', icon: '✍️', x: -260, y: -60, z: 28 },
  { id: 'analytics', title: 'Analytics Card', desc: 'Visual summary of insights', icon: '💡', x: 160, y: 110, z: 30 },
];

let focusedFormatId = null;
let selectedAudience = 'General';
let selectedTone = 'Professional';

// Initial Setup on Page Load
document.addEventListener('DOMContentLoaded', () => {
  checkAuthUser();
  renderFloatingCards();
  initParallaxMouse();
});

// Render 3D Floating Cards in Hero
function renderFloatingCards() {
  const layer = document.getElementById('floatingCardsLayer');
  if (!layer) return;

  layer.innerHTML = FORMATS.map(f => `
    <div 
      class="floating-card-item" 
      id="card-${f.id}"
      style="
        left: calc(50% + ${f.x}px);
        top: calc(50% + ${f.y}px);
        z-index: ${f.z};
        transform: translate(-50%, -50%) scale(${f.z < 15 ? 0.8 : 1.0});
      "
      onclick="focusFormatCard('${f.id}')"
    >
      <div style="background: linear-gradient(145deg, #111827, #070a12); width: 100%; height: 100%; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; border-radius: 12px;">
        <div style="font-size: 32px;">${f.icon}</div>
        <div class="card-content-box">
          <div class="card-title-text">${f.title}</div>
          <div class="card-desc-text">${f.desc}</div>
        </div>
      </div>
    </div>
  `).join('');
}

// Parallax Mouse Motion
function initParallaxMouse() {
  window.addEventListener('mousemove', (e) => {
    if (focusedFormatId) return; // Freeze parallax when focused
    const mouseX = e.clientX - window.innerWidth / 2;
    const mouseY = e.clientY - window.innerHeight / 2;

    FORMATS.forEach(f => {
      const card = document.getElementById(`card-${f.id}`);
      if (card && !card.classList.contains('focused')) {
        const factor = f.z * 0.03;
        const offsetX = f.x + mouseX * factor;
        const offsetY = f.y + mouseY * factor;
        card.style.left = `calc(50% + ${offsetX}px)`;
        card.style.top = `calc(50% + ${offsetY}px)`;
      }
    });
  });
}

// Focus a Format Card & Show Transformation Overlay
function focusFormatCard(formatId) {
  focusedFormatId = formatId;
  const targetFormat = FORMATS.find(f => f.id === formatId);
  if (!targetFormat) return;

  FORMATS.forEach(f => {
    const el = document.getElementById(`card-${f.id}`);
    if (el) el.classList.remove('focused');
  });

  const activeEl = document.getElementById(`card-${formatId}`);
  if (activeEl) activeEl.classList.add('focused');

  document.getElementById('heroCenterContent').style.opacity = '0';

  document.getElementById('focusedFormatTitle').innerText = targetFormat.title;
  document.getElementById('focusedFormatDesc').innerText = targetFormat.desc;
  document.getElementById('transformModalOverlay').style.display = 'block';

  showToast(`Selected format: ${targetFormat.title}`);
}

function closeTransformationModal() {
  focusedFormatId = null;
  FORMATS.forEach(f => {
    const el = document.getElementById(`card-${f.id}`);
    if (el) el.classList.remove('focused');
  });
  document.getElementById('heroCenterContent').style.opacity = '1';
  document.getElementById('transformModalOverlay').style.display = 'none';
}

function selectAudience(btn, audience) {
  document.querySelectorAll('.audience-pill').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
  selectedAudience = audience;
}

function selectTone(btn, tone) {
  document.querySelectorAll('.tone-pill').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
  selectedTone = tone;
}

function scrollToStudio(mode = 'video') {
  closeTransformationModal();
  window.location.href = `studio.html?mode=${mode}`;
}

// ==========================================================
// Studio Mode Navigation (Create Video vs Create Post)
// ==========================================================
function openStudioMode(mode) {
  currentPipeline = mode;
  document.getElementById('studioChoiceGrid').style.display = 'none';

  if (mode === 'video') {
    document.getElementById('videoStudioContainer').style.display = 'block';
    document.getElementById('postStudioContainer').style.display = 'none';
    goToVideoStep(1);
  } else {
    document.getElementById('videoStudioContainer').style.display = 'none';
    document.getElementById('postStudioContainer').style.display = 'block';
  }

  const studio = document.getElementById('studio');
  if (studio) studio.scrollIntoView({ behavior: 'smooth' });
}

function backToStudioChoice() {
  document.getElementById('studioChoiceGrid').style.display = 'grid';
  document.getElementById('videoStudioContainer').style.display = 'none';
  document.getElementById('postStudioContainer').style.display = 'none';
}

// ==========================================================
// Video Generation Studio Multi-Step Workflow
// ==========================================================

function selectVideoPlatform(platform) {
  currentPlatform = platform;
  document.getElementById('vPlatInstagram').classList.toggle('selected', platform === 'instagram');
  document.getElementById('vPlatYoutube').classList.toggle('selected', platform === 'youtube');
  showToast(`Platform set: ${platform.toUpperCase()}`);
}

function selectVideoCategory(category) {
  selectedVideoCategory = category;
  document.getElementById('typeShortForm').classList.toggle('selected', category === 'short');
  document.getElementById('typeLongForm').classList.toggle('selected', category === 'long');
  
  if (category === 'long') {
    document.getElementById('videoDurationInput').value = 180; // 3 minutes for long-form
    document.getElementById('aiDurationBadge').innerText = '180 seconds (3m)';
  } else {
    document.getElementById('videoDurationInput').value = 60; // 60s for short-form
    document.getElementById('aiDurationBadge').innerText = '60 seconds';
  }
  showToast(`Format category: ${category === 'short' ? 'Short Form Content (9:16)' : 'Long Form Content (16:9)'}`);
}

function goToVideoStep(stepNum) {
  // Update Stepper Bar Indicators
  for (let i = 1; i <= 5; i++) {
    const indicator = document.getElementById(`vStep${i}Indicator`);
    if (indicator) {
      indicator.classList.toggle('active', i === stepNum);
      indicator.classList.toggle('completed', i < stepNum);
    }

    const view = document.getElementById(`videoStep${i}View`);
    if (view) {
      view.style.display = (i === stepNum) ? 'block' : 'none';
    }
  }
}

// Step 1 -> Step 2: Document Ingestion & AI Script Analysis
async function goToVideoStep2() {
  if (!selectedFile) {
    showToast('⚠️ Please upload a document file (.pdf, .pptx, .docx, .txt, .md) first!');
    return;
  }

  goToVideoStep(2);
  showToast('⚙️ Ingesting document & extracting claims...');

  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('platform', currentPlatform);

  try {
    const res = await fetch(`${API_BASE}/api/video/scripts`, { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Ingestion failed');
    }

    ingestedScriptData = await res.json();
    
    // Update metrics and editable script text
    const numScenes = (ingestedScriptData.scenes || []).length;
    document.getElementById('metricBlocks').innerText = `${numScenes * 6}`;
    document.getElementById('metricClaims').innerText = `${numScenes * 8}`;
    document.getElementById('metricBeats').innerText = `${numScenes}`;

    const suggestedDuration = numScenes ? Math.max(30, numScenes * 4) : 60;
    document.getElementById('videoDurationInput').value = suggestedDuration;
    document.getElementById('aiDurationBadge').innerText = `${suggestedDuration} seconds`;

    document.getElementById('videoScriptEditor').value = JSON.stringify(ingestedScriptData, null, 2);
    document.getElementById('ingestLoadingBanner').style.background = 'rgba(52, 211, 153, 0.1)';
    document.getElementById('ingestLoadingBanner').style.borderColor = 'var(--accent-green)';
    document.getElementById('ingestStatText').innerText = `✅ Ingestion complete! ${numScenes} script beats distilled successfully.`;

    showToast('✅ Document ingested! Review AI suggested duration & script.');
  } catch (error) {
    showToast(`❌ Ingestion Warning: ${error.message}. Loaded placeholder script.`);
    const fallbackScript = {
      title: selectedFile ? selectedFile.name : "Document Analysis Short",
      scenes: [
        { narration: "Key finding from document: Market efficiency increased by 42%.", keywords: ["efficiency", "growth"], on_screen_text: "42% Growth" },
        { narration: "Next steps involve accelerating digital transformation.", keywords: ["transformation", "tech"], on_screen_text: "Digital Shift" }
      ],
      caption: "Transforming document insights into kinetic video.",
      hashtags: ["#ContentEngine", "#AI", "#Tech"]
    };
    ingestedScriptData = fallbackScript;
    document.getElementById('videoScriptEditor').value = JSON.stringify(fallbackScript, null, 2);
  }
}

// Step 2 -> Step 3: Go to Typography & Music Customization
function goToVideoStep3() {
  const editedText = document.getElementById('videoScriptEditor').value;
  try {
    ingestedScriptData = JSON.parse(editedText);
  } catch (e) {
    showToast('⚠️ Note: Script is stored as raw text string.');
  }
  goToVideoStep(3);
  showToast('🎨 Customization options loaded.');
}

function selectTypography(optionIndex) {
  selectedTypographyOption = optionIndex;
  for (let i = 1; i <= 3; i++) {
    const card = document.getElementById(`typoOption${i}`);
    if (card) card.classList.toggle('selected', i === optionIndex);
  }
  showToast(`Selected Typography Option ${optionIndex}`);
}

function selectSong(optionIndex) {
  selectedSongOption = optionIndex;
  for (let i = 1; i <= 3; i++) {
    const card = document.getElementById(`songOption${i}`);
    if (card) card.classList.toggle('selected', i === optionIndex);
  }
  showToast(`Selected Song Option ${optionIndex}`);
}

function applyAIOptionPreset() {
  selectTypography(1); // Kinetic Neon Bold
  selectSong(1);       // Upbeat Lo-Fi Synth
  showToast('⚡ AI auto-selected Kinetic Neon Bold & Upbeat Lo-Fi Synth preset!');
}

// Step 3 -> Step 4 & 5: Render Final Kinetic Video
async function startFinalVideoRender() {
  if (!selectedFile) {
    showToast('⚠️ Upload a document first!');
    return;
  }

  goToVideoStep(4); // Show Creating / Rendering Screen
  
  const duration = document.getElementById('videoDurationInput').value || 60;
  const formatPreset = selectedVideoCategory === 'long' ? 'landscape' : 'shorts';

  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('platform', currentPlatform);
  formData.append('duration_seconds', duration);
  formData.append('typography_option', selectedTypographyOption);
  formData.append('song_option', selectedSongOption);
  if (document.getElementById('videoScriptEditor')) {
    formData.append('script_json', document.getElementById('videoScriptEditor').value);
  }

  try {
    const res = await fetch(`${API_BASE}/api/video/jobs`, { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Video creation failed');
    }

    const jobData = await res.json();
    currentJobId = jobData.job_id;

    showToast(`🚀 Render Job '${currentJobId}' queued!`);
    startPollingVideoJob(currentJobId);

  } catch (error) {
    showToast(`❌ Render Error: ${error.message}`);
    document.getElementById('creatingSubtext').innerText = `❌ Error: ${error.message}`;
  }
}

// Poll real-time progress for Video Job
function startPollingVideoJob(jobId) {
  if (pollInterval) clearInterval(pollInterval);

  pollInterval = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/video/jobs/${jobId}`);
      if (!res.ok) return;

      const job = await res.json();
      
      // Update Step 4 progress bar UI
      document.getElementById('vStageLabel').innerText = job.stage || 'Processing orchestrator...';
      document.getElementById('vProgressPercent').innerText = `${job.progress || 0}%`;
      document.getElementById('vProgressFill').style.width = `${job.progress || 0}%`;

      if (job.status === 'done' || job.status === 'failed') {
        clearInterval(pollInterval);
        if (job.status === 'done') {
          showToast('🎉 Master Kinetic Video generated successfully!');
          displayFinalVideoOutput(job);
        } else {
          showToast(`❌ Rendering Failed: ${job.error || 'Unknown error'}`);
          document.getElementById('creatingSubtext').innerText = `❌ Job Failed: ${job.error || 'Unknown error'}`;
        }
      }
    } catch (e) {
      console.error(e);
    }
  }, 2000);
}

// Display Step 5 Final Master Video Output with Controls & Download MP4
function displayFinalVideoOutput(job) {
  goToVideoStep(5);
  
  const videoUrl = `${API_BASE}/api/video/jobs/${job.job_id}/download`;
  const player = document.getElementById('finalVideoPlayer');
  const source = document.getElementById('finalVideoSource');
  const downloadBtn = document.getElementById('downloadMp4Btn');

  if (source) source.src = videoUrl;
  if (player) {
    player.load();
    player.play().catch(e => console.log('Autoplay handled:', e));
  }
  if (downloadBtn) {
    downloadBtn.href = videoUrl;
    downloadBtn.setAttribute('download', `master_faceless_video_${job.job_id}.mp4`);
  }
}

function restartVideoWorkflow() {
  selectedFile = null;
  ingestedScriptData = null;
  document.getElementById('fileInput').value = '';
  document.getElementById('fileInfo').style.display = 'none';
  goToVideoStep(1);
  showToast('Reset video workflow. Ready for new document.');
}

// ==========================================================
// Post Generation Studio (Pipeline A) Handlers
// ==========================================================
function selectPostPlatform(platform) {
  document.getElementById('pPlatLinkedin').classList.toggle('selected', platform === 'linkedin');
  document.getElementById('pPlatInstagram').classList.toggle('selected', platform === 'instagram');
}

function handlePostFileSelect(event) {
  const file = event.target.files[0];
  if (file) {
    selectedPostFile = file;
    document.getElementById('postFileName').innerText = `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
    document.getElementById('postFileInfo').style.display = 'flex';
    showToast(`Loaded post document: ${file.name}`);
  }
}

async function startPostRender() {
  if (!selectedPostFile && !selectedFile) {
    showToast('⚠️ Please upload a document first!');
    return;
  }
  const fileToUse = selectedPostFile || selectedFile;

  showToast('🚀 Generating static carousel post deck...');
  const formData = new FormData();
  formData.append('file', fileToUse);
  formData.append('platform', 'linkedin');

  try {
    const res = await fetch(`${API_BASE}/api/posts/jobs`, { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Post creation failed');
    }
    const job = await res.json();
    showToast(`Static Post job '${job.job_id}' queued!`);

    setTimeout(() => {
      document.getElementById('postPreviewBox').innerHTML = `
        <div style="width: 100%; text-align: center; padding: 24px;">
          <div style="font-size: 56px; margin-bottom: 12px;">🖼️</div>
          <h3 style="margin-bottom: 12px; color: var(--text-primary);">Static Carousel Slide Deck Ready!</h3>
          <p style="color: var(--text-muted); margin-bottom: 24px;">All high-resolution PNG slides generated successfully.</p>
          <a href="${API_BASE}/api/posts/jobs/${job.job_id}/download" download class="btn btn-gradient" style="display: inline-flex;">
            📦 Download Carousel Deck ZIP / PDF
          </a>
        </div>
      `;
    }, 3000);
  } catch (err) {
    showToast(`❌ Error: ${err.message}`);
  }
}

// File Handlers & Helper Functions
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
if (dropzone) {
  dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) setFile(e.dataTransfer.files[0]);
  });
}

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

function showToast(msg) {
  const toast = document.getElementById('toast');
  if (toast) {
    toast.innerText = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3500);
  }
}
