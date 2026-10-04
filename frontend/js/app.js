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
  initScrollSpy();
  initArtifactCardInteractions();
  checkUrlParamsStudioMode();
  initCinematicHeroScroll();
});

// ScrollSpy for Top Navbar Link Underline Transition
function initScrollSpy() {
  const navLinks = document.querySelectorAll('nav a[href^="#"]');
  if (!navLinks.length) return;

  const sections = Array.from(navLinks)
    .map(link => {
      const hash = link.getAttribute('href');
      if (!hash || hash === '#') return null;
      return document.querySelector(hash);
    })
    .filter(Boolean);

  if (!sections.length) return;

  function updateActiveLink() {
    const scrollPosition = window.scrollY + 200; // Offset for sticky top bar

    let currentSection = sections[0];
    for (const section of sections) {
      if (section.offsetTop <= scrollPosition) {
        currentSection = section;
      }
    }

    if (currentSection) {
      const activeId = currentSection.getAttribute('id');
      navLinks.forEach(link => {
        const isMatch = link.getAttribute('href') === `#${activeId}`;
        if (isMatch) {
          link.className = 'nav-item text-primary dark:text-surface-bright font-bold border-b-2 border-primary dark:border-surface-bright pb-1 transition-colors';
        } else {
          link.className = 'nav-item text-secondary dark:text-outline-variant hover:text-primary dark:hover:text-surface-bright pb-1 transition-colors';
        }
      });
    }
  }

  window.addEventListener('scroll', updateActiveLink);
  updateActiveLink(); // Initial check
}

// 3D Tilt & Mouse Tracking Interaction for the 3 Feature Artifact Cards
function initArtifactCardInteractions() {
  const cards = document.querySelectorAll('.feature-artifact-card');
  if (!cards.length) return;

  cards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      
      // Dynamic tilt angles (max ~6 degrees)
      const rotateX = ((y - centerY) / centerY) * -6;
      const rotateY = ((x - centerX) / centerX) * 6;
      
      card.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-8px) scale(1.025)`;
      card.style.setProperty('--mouse-x', `${((x / rect.width) * 100).toFixed(1)}%`);
      card.style.setProperty('--mouse-y', `${((y / rect.height) * 100).toFixed(1)}%`);
    });

    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
      card.style.removeProperty('--mouse-x');
      card.style.removeProperty('--mouse-y');
    });
  });
}

// Render 3D Floating Cards in Hero
function renderFloatingCards() {
  const layer = document.getElementById('floatingCardsLayer');
  if (!layer) return;

  const extMap = {
    linkedin: '.post',
    twitter: '.tweet',
    presentation: '.slide',
    executive: '.brief',
    advisory: '.report',
    infographic: '.chart',
    storyboard: '.story',
    youtube: '.shorts',
    instagram: '.reel',
    email: '.mail',
    press: '.press',
    research: '.paper',
    mobile: '.card',
    blog: '.doc',
    analytics: '.data'
  };

  layer.innerHTML = FORMATS.map((f, idx) => {
    const ext = extMap[f.id] || '.doc';
    const cardZ = Math.min(15, f.z); // Keep z-index <= 15 so all cards stay BEHIND heroCenterContent (z-40)

    return `
      <div 
        class="floating-card-item" 
        id="card-${f.id}"
        style="
          left: calc(50% + ${f.x}px);
          top: calc(50% + ${f.y}px);
          z-index: ${cardZ};
          transform: translate(-50%, -50%) scale(${f.z < 15 ? 0.85 : 1.0});
        "
        onclick="focusFormatCard('${f.id}')"
      >
        <div class="scrapbook-card hand-drawn-pill">
          <div style="width: 36px; height: 36px; border-radius: 10px; background: #F3EDE2; border: 1px solid #DDD5C5; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0;">${f.icon}</div>
          <div class="card-content-box" style="min-width: 0; flex: 1;">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 4px;">
              <span class="card-title-text" style="font-family: 'Patrick Hand', 'Gochi Hand', cursive; font-size: 13px; font-weight: 700; color: #2C2924; text-transform: uppercase; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${f.title}</span>
              <span style="font-family: 'Fira Code', monospace; font-size: 10px; font-weight: 700; background: #dce6d8; color: #335328; padding: 1px 5px; border-radius: 4px; border: 1px solid rgba(45,55,46,0.3); line-height: 1.2;">${ext}</span>
            </div>
            <div class="card-desc-text" style="font-family: 'Patrick Hand', cursive; font-size: 11px; color: #746E65; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px;">${f.desc}</div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// Parallax Mouse Motion (Disabled per user request so tags remain static)
function initParallaxMouse() {
  // Static layout - no cursor parallax tracking on floating cards
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
  const workbench = document.getElementById('workbench') || document.getElementById('studioChoiceGrid');
  if (workbench) {
    workbench.scrollIntoView({ behavior: 'smooth' });
  } else {
    window.location.href = `studio.html?mode=${mode}`;
  }
}

// ==========================================================
// Studio Mode Navigation (Create Video vs Create Post)
// ==========================================================
function openStudioMode(mode, documentKind = null) {
  currentPipeline = mode;

  const videoContainer = document.getElementById('videoStudioContainer');
  if (!videoContainer) {
    // We are on landing page index.html: Navigate to the separate dedicated studio page
    const kindQuery = documentKind ? `&kind=${encodeURIComponent(documentKind)}` : '';
    window.location.href = `studio.html?mode=${mode}${kindQuery}`;
    return;
  }

  // We are on dedicated studio.html: Toggle studio views
  const choiceGrid = document.getElementById('studioChoiceGrid');
  if (choiceGrid) choiceGrid.style.display = 'none';

  const postContainer = document.getElementById('postStudioContainer');
  const presContainer = document.getElementById('presentationStudioContainer');
  const documentContainer = document.getElementById('businessDocumentStudioContainer');

  if (mode === 'select') {
    if (choiceGrid) choiceGrid.style.display = 'grid';
    videoContainer.style.display = 'none';
    if (postContainer) postContainer.style.display = 'none';
    if (presContainer) presContainer.style.display = 'none';
    if (documentContainer) documentContainer.style.display = 'none';
  } else if (mode === 'video') {
    videoContainer.style.display = 'block';
    if (postContainer) postContainer.style.display = 'none';
    if (presContainer) presContainer.style.display = 'none';
    if (documentContainer) documentContainer.style.display = 'none';
    goToVideoStep(1);
  } else if (mode === 'presentation') {
    videoContainer.style.display = 'none';
    if (postContainer) postContainer.style.display = 'none';
    if (presContainer) presContainer.style.display = 'block';
    if (documentContainer) documentContainer.style.display = 'none';
    goToPresentationStep(1);
  } else if (mode === 'document' || mode === 'documents') {
    videoContainer.style.display = 'none';
    if (postContainer) postContainer.style.display = 'none';
    if (presContainer) presContainer.style.display = 'none';
    if (documentContainer) documentContainer.style.display = 'block';
    if (documentKind) selectBusinessDocumentKind(documentKind);
    showBusinessDocumentView('plan');
  } else {
    videoContainer.style.display = 'none';
    if (postContainer) postContainer.style.display = 'block';
    if (presContainer) presContainer.style.display = 'none';
    if (documentContainer) documentContainer.style.display = 'none';
  }

  const studio = document.getElementById('studio');
  if (studio) studio.scrollIntoView({ behavior: 'smooth' });
}

async function generatePresentationDeck() {
  const fileInput = document.getElementById('presFileInput');
  const urlInput = document.getElementById('presUrlInput');
  const promptInput = document.getElementById('presPromptInput');
  const themeSelect = document.getElementById('presThemeSelect');
  const statusText = document.getElementById('presStatusText');
  const previewBox = document.getElementById('presDeckPreview');
  const downloadGroup = document.getElementById('presDownloadGroup');

  const file = fileInput ? fileInput.files[0] : null;
  const url = urlInput ? urlInput.value.trim() : '';
  const prompt = promptInput ? promptInput.value.trim() : '';
  const theme = themeSelect ? themeSelect.value : 'bold_tech';

  if (!file && !url && !prompt) {
    alert('Please select a file, enter a Web URL, or type a topic request prompt.');
    return;
  }

  if (statusText) statusText.innerText = 'Creating presentation job...';
  if (previewBox) previewBox.innerHTML = '<div class="animate-spin text-3xl">⏳</div><div class="font-hand font-bold mt-2">AI is synthesizing slides...</div>';

  try {
    let endpoint = '/api/presentation/jobs';
    let formData = new FormData();
    formData.append('theme', theme);

    if (file) {
      formData.append('file', file);
    } else if (url) {
      endpoint = '/api/presentation/jobs/from-url';
      formData = JSON.stringify({ url: url, theme: theme });
    } else if (prompt) {
      endpoint = '/api/presentation/jobs/from-prompt';
      formData = JSON.stringify({ prompt: prompt, theme: theme });
    }

    const headers = {};
    if (endpoint !== '/api/presentation/jobs') {
      headers['Content-Type'] = 'application/json';
    }

    const resp = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: headers,
      body: formData
    });

    if (!resp.ok) throw new Error(`Server returned ${resp.status}`);
    const job = await resp.json();

    pollPresentationJob(job.job_id);
  } catch (err) {
    if (statusText) statusText.innerText = `Error: ${err.message}`;
    if (previewBox) previewBox.innerHTML = `<span class="text-red-600 font-bold">Failed to create presentation: ${err.message}</span>`;
  }
}

async function pollPresentationJob(jobId) {
  const statusText = document.getElementById('presStatusText');
  const previewBox = document.getElementById('presDeckPreview');
  const downloadGroup = document.getElementById('presDownloadGroup');

  const interval = setInterval(async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/presentation/jobs/${jobId}`);
      if (!resp.ok) return;
      const job = await resp.json();

      if (statusText) statusText.innerText = `Status: ${job.stage} (${job.progress}%)`;

      if (job.status === 'done') {
        clearInterval(interval);
        if (statusText) statusText.innerText = 'Presentation Slide Deck ready!';

        const slides = job.script ? job.script.slides || [] : [];
        const slidesSummary = slides.map(s => `<div class="text-xs p-2 bg-white rounded border border-charcoal/30 my-1"><b>Slide ${s.idx}:</b> ${s.heading}</div>`).join('');

        if (previewBox) {
          previewBox.innerHTML = `
            <div class="text-left w-full max-h-48 overflow-y-auto">
              <div class="font-bold text-sm text-charcoal mb-2">🎉 ${job.script ? job.script.title : 'Presentation'} (${slides.length} slides)</div>
              ${slidesSummary}
            </div>
          `;
        }

        if (downloadGroup) {
          downloadGroup.style.display = 'block';
          document.getElementById('btnPresDownloadHtml').href = `${API_BASE}/api/presentation/jobs/${jobId}/download?format=html_view`;
          document.getElementById('btnPresDownloadPdf').href = `${API_BASE}/api/presentation/jobs/${jobId}/download?format=pdf`;
          document.getElementById('btnPresDownloadPptx').href = `${API_BASE}/api/presentation/jobs/${jobId}/download?format=pptx`;
        }
      } else if (job.status === 'failed') {
        clearInterval(interval);
        if (statusText) statusText.innerText = `Failed: ${job.error}`;
      }
    } catch (e) {}
  }, 2000);
}

// ==========================================================
// Business documents: source -> editable review -> HTML/PDF render
// ==========================================================
let selectedBusinessDocumentKind = 'executive';
let businessDocumentDraft = null;

function selectBusinessDocumentKind(kind) {
  selectedBusinessDocumentKind = kind === 'advisory' ? 'advisory' : 'executive';
  document.querySelectorAll('[data-document-kind]').forEach((button) => {
    const active = button.dataset.documentKind === selectedBusinessDocumentKind;
    button.classList.toggle('ring-4', active);
    button.classList.toggle('ring-terracotta', active);
    button.setAttribute('aria-pressed', active ? 'true' : 'false');
  });
  const heading = document.getElementById('docStudioTitle');
  if (heading) heading.textContent = selectedBusinessDocumentKind === 'executive' ? 'Executive Summary Studio' : 'Advisory Report Studio';
}

function showBusinessDocumentView(view) {
  ['plan', 'review', 'final'].forEach((name) => {
    const element = document.getElementById(`doc${name[0].toUpperCase()}${name.slice(1)}View`);
    if (element) element.style.display = name === view ? 'block' : 'none';
  });
}

function documentCitationChips(citations = []) {
  return citations.map((citation) => `<span class="inline-block mt-2 mr-1 px-2 py-0.5 rounded-full bg-moss-surface border border-moss/30 text-moss-dark text-xs font-hand font-bold" title="${escapePresentationHtml(citation.excerpt || '')}">${escapePresentationHtml(citation.locator || '')}</span>`).join('');
}

function businessDocumentItemEditor(group, index, item, fields) {
  const inputs = fields.map(({ key, label, multiline = false, options = null }) => {
    const value = escapePresentationHtml(item[key] || '');
    if (options) {
      return `<label class="font-hand font-bold text-sm">${label}<select data-document-group="${group}" data-document-index="${index}" data-document-field="${key}" class="mt-1 w-full p-2 bg-paper-tint/40 border-2 border-charcoal rounded-xl font-hand font-normal">${options.map((option) => `<option value="${option}" ${item[key] === option ? 'selected' : ''}>${option}</option>`).join('')}</select></label>`;
    }
    const control = multiline
      ? `<textarea data-document-group="${group}" data-document-index="${index}" data-document-field="${key}" rows="3" class="mt-1 w-full p-2 bg-paper-tint/40 border-2 border-charcoal rounded-xl font-hand font-normal">${value}</textarea>`
      : `<input data-document-group="${group}" data-document-index="${index}" data-document-field="${key}" value="${value}" class="mt-1 w-full p-2 bg-paper-tint/40 border-2 border-charcoal rounded-xl font-hand font-normal">`;
    return `<label class="font-hand font-bold text-sm ${multiline ? 'md:col-span-2' : ''}">${label}${control}</label>`;
  }).join('');
  return `<article class="bg-white border-2 border-charcoal rounded-2xl p-4 shadow-sketch-sm"><div class="flex items-center justify-between gap-3 mb-3"><span class="font-sketch text-lg font-bold">${group.replaceAll('_', ' ')}</span><button type="button" class="px-3 py-1 bg-[#ffe8e2] border border-charcoal rounded-lg font-hand font-bold text-sm" onclick="removeBusinessDocumentItem('${group}', ${index})">Remove</button></div><div class="grid grid-cols-1 md:grid-cols-2 gap-3">${inputs}</div><div class="mt-2 border-t border-charcoal/15 pt-1"><span class="font-hand text-xs font-bold text-charcoal/65">Locked source citations</span><div>${documentCitationChips(item.citations)}</div></div></article>`;
}

function renderBusinessDocumentEditor() {
  if (!businessDocumentDraft) return;
  const draft = businessDocumentDraft;
  const title = document.getElementById('docDraftTitle');
  const audience = document.getElementById('docDraftAudience');
  const narrative = document.getElementById('docDraftNarrative');
  const narrativeLabel = document.getElementById('docDraftNarrativeLabel');
  const editors = document.getElementById('docItemEditors');
  if (title) title.value = draft.title || '';
  if (audience) audience.value = draft.audience || 'Executive leadership';
  const isExecutive = draft.kind === 'executive';
  if (narrative) narrative.value = isExecutive ? draft.overview : draft.assessment;
  if (narrativeLabel) narrativeLabel.textContent = isExecutive ? 'Executive overview' : 'Assessment';
  if (!editors) return;

  const groups = isExecutive
    ? [
      ['key_findings', draft.key_findings, [{ key: 'heading', label: 'Finding' }, { key: 'detail', label: 'Evidence-backed detail', multiline: true }]],
      ['implications', draft.implications, [{ key: 'heading', label: 'Implication' }, { key: 'detail', label: 'Evidence-backed detail', multiline: true }]],
      ['decision_requests', draft.decision_requests, [{ key: 'action', label: 'Decision request' }, { key: 'rationale', label: 'Rationale', multiline: true }]],
      ['priority_actions', draft.priority_actions, [{ key: 'action', label: 'Priority action' }, { key: 'rationale', label: 'Rationale', multiline: true }]],
    ]
    : [
      ['risks', draft.risks, [{ key: 'title', label: 'Risk / review area' }, { key: 'severity', label: 'Severity', options: ['low', 'medium', 'high', 'critical'] }, { key: 'impact', label: 'Impact', multiline: true }]],
      ['recommendations', draft.recommendations, [{ key: 'recommendation', label: 'Recommendation' }, { key: 'priority', label: 'Priority', options: ['now', 'next', 'monitor'] }, { key: 'timeframe', label: 'Timeframe' }, { key: 'rationale', label: 'Rationale', multiline: true }]],
      ['immediate_next_steps', draft.immediate_next_steps, [{ key: 'action', label: 'Immediate next step' }, { key: 'rationale', label: 'Rationale', multiline: true }]],
    ];
  editors.innerHTML = groups.map(([group, items, fields]) => `<section class="space-y-3"><h3 class="font-sketch text-xl font-bold text-moss-dark capitalize mt-6">${group.replaceAll('_', ' ')}</h3>${items.map((item, index) => businessDocumentItemEditor(group, index, item, fields)).join('')}</section>`).join('');
}

function syncBusinessDocumentDraft() {
  if (!businessDocumentDraft) return;
  const title = document.getElementById('docDraftTitle');
  const audience = document.getElementById('docDraftAudience');
  const narrative = document.getElementById('docDraftNarrative');
  businessDocumentDraft.title = title?.value.trim() || businessDocumentDraft.title;
  businessDocumentDraft.audience = audience?.value.trim() || 'Executive leadership';
  if (businessDocumentDraft.kind === 'executive') businessDocumentDraft.overview = narrative?.value.trim() || businessDocumentDraft.overview;
  else businessDocumentDraft.assessment = narrative?.value.trim() || businessDocumentDraft.assessment;
  document.querySelectorAll('[data-document-group]').forEach((field) => {
    const item = businessDocumentDraft[field.dataset.documentGroup]?.[Number(field.dataset.documentIndex)];
    if (item) item[field.dataset.documentField] = field.value.trim();
  });
}

function removeBusinessDocumentItem(group, index) {
  syncBusinessDocumentDraft();
  const items = businessDocumentDraft?.[group];
  if (!items || items.length <= 1) {
    showToast('At least one source-cited item is required in each section.');
    return;
  }
  items.splice(index, 1);
  renderBusinessDocumentEditor();
}

async function createBusinessDocumentPlan() {
  const file = document.getElementById('docFileInput')?.files[0];
  const url = document.getElementById('docUrlInput')?.value.trim();
  const prompt = document.getElementById('docPromptInput')?.value.trim();
  const audience = document.getElementById('docAudienceInput')?.value.trim() || 'Executive leadership';
  const statusText = document.getElementById('docPlanStatus');
  if (!file && !url && !prompt) {
    if (statusText) statusText.textContent = 'Add a file, URL, or topic before creating a draft.';
    return;
  }
  const payload = new FormData();
  payload.append('kind', selectedBusinessDocumentKind);
  payload.append('audience', audience);
  if (file) payload.append('file', file); else if (url) payload.append('url', url); else payload.append('prompt', prompt);
  if (statusText) statusText.textContent = 'Analysing source evidence and creating your editable draft…';
  try {
    const response = await fetch(`${API_BASE}/api/documents/plan`, { method: 'POST', body: payload });
    if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || `Server returned ${response.status}`);
    const plan = await response.json();
    businessDocumentDraft = plan.draft;
    renderBusinessDocumentEditor();
    showBusinessDocumentView('review');
  } catch (error) {
    if (statusText) statusText.textContent = `Could not create the draft: ${error.message}`;
  }
}

async function renderApprovedBusinessDocument() {
  syncBusinessDocumentDraft();
  const statusText = document.getElementById('docRenderStatus');
  if (!businessDocumentDraft) return;
  if (statusText) statusText.textContent = 'Submitting your approved, source-cited document…';
  try {
    const response = await fetch(`${API_BASE}/api/documents/jobs/from-draft`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(businessDocumentDraft) });
    if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || `Server returned ${response.status}`);
    showBusinessDocumentView('final');
    pollBusinessDocumentJob((await response.json()).job_id);
  } catch (error) {
    if (statusText) statusText.textContent = `Could not start rendering: ${error.message}`;
  }
}

function pollBusinessDocumentJob(jobId) {
  const statusText = document.getElementById('docFinalStatus');
  const output = document.getElementById('docOutputPreview');
  const interval = setInterval(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/documents/jobs/${jobId}`);
      if (!response.ok) throw new Error(`Server returned ${response.status}`);
      const job = await response.json();
      if (statusText) statusText.textContent = `${job.stage} (${job.progress}%)`;
      if (job.status === 'done') {
        clearInterval(interval);
        const htmlUrl = `${API_BASE}/api/documents/jobs/${jobId}/download?format=html_view`;
        const pdfUrl = `${API_BASE}/api/documents/jobs/${jobId}/download?format=pdf`;
        if (output) output.innerHTML = `<iframe title="Generated business document" src="${htmlUrl}" class="w-full min-h-[540px] bg-white rounded-xl border-2 border-charcoal"></iframe><div class="mt-4 flex flex-col sm:flex-row gap-3"><a target="_blank" href="${htmlUrl}" class="px-5 py-2 bg-blue-600 text-white text-center font-sketch font-bold rounded-xl border-2 border-charcoal">Open HTML</a><a download href="${pdfUrl}" class="px-5 py-2 bg-red-600 text-white text-center font-sketch font-bold rounded-xl border-2 border-charcoal">Download PDF</a></div>`;
      } else if (job.status === 'failed') {
        clearInterval(interval);
        if (statusText) statusText.textContent = `Rendering failed: ${job.error || 'Unknown error'}`;
      }
    } catch (error) {
      clearInterval(interval);
      if (statusText) statusText.textContent = `Could not check render status: ${error.message}`;
    }
  }, 1500);
}

// ==========================================================
// Presentation workflow: ingest -> edit slide plan -> design -> render
// ==========================================================
let presentationDeckDraft = null;
let selectedPresentationTheme = 'bold_tech';
let currentPresentationStep = 1;
let presentationPreviewDeck = null;
let presentationPreviewIndex = 0;

const PRESENTATION_LAYOUTS = [
  ['title_hero', 'Title hero'],
  ['big_stat', 'Big stat'],
  ['feature_cards', 'Feature cards'],
  ['split_image_text', 'Split image + text'],
  ['process_stepper', 'Process stepper'],
  ['quote_card', 'Quote card'],
  ['comparison_table', 'Comparison table'],
  ['end_cta', 'End CTA']
];

const PRESENTATION_PREVIEW_THEMES = {
  bold_tech: { background: '#0b0f19', surface: '#141c2e', primary: '#f8fafc', secondary: '#94a3b8', accent: '#38bdf8' },
  minimalist_editorial: { background: '#fcf8f3', surface: '#ffffff', primary: '#1f1b15', secondary: '#536349', accent: '#904c30' },
  neon_cyberpunk: { background: '#090d16', surface: '#131b2e', primary: '#ffffff', secondary: '#a1a1aa', accent: '#ec4899' },
  warm_corporate: { background: '#fff8f3', surface: '#f0e7dc', primary: '#1f1b15', secondary: '#4a663e', accent: '#4a663e' }
};

// Keep the in-app preview visually aligned with the renderer's shared
// decorative pack. Exported HTML, PDF, and PPTX use the same assets directly.
const PRESENTATION_PREVIEW_STICKERS = {
  bold_tech: ['code_brackets.png', 'cursor.png', 'brain.png'],
  minimalist_editorial: ['circle_ring.png', 'arrow_up_right.png', 'star_four_gold.png'],
  neon_cyberpunk: ['lightning_purple.png', 'rocket.png', 'sparkle_purple.png'],
  warm_corporate: ['chart_up.png', 'target.png', 'arrow_up_right.png']
};

function goToPresentationStep(stepNum) {
  currentPresentationStep = stepNum;
  for (let i = 1; i <= 5; i++) {
    const indicator = document.getElementById(`pStep${i}Indicator`);
    if (indicator) {
      const badge = indicator.querySelector('span:first-child');
      if (i === stepNum) {
        indicator.className = 'flex items-center gap-2 flex-shrink-0 px-3.5 py-1.5 rounded-xl bg-terracotta-soft text-terracotta border-2 border-charcoal font-hand font-bold text-base shadow-sketch-sm transition-all';
        if (badge) {
          badge.className = 'w-6 h-6 rounded-full bg-terracotta text-white font-sans text-xs font-bold flex items-center justify-center border border-charcoal';
          badge.innerText = `${i}`;
        }
      } else if (i < stepNum) {
        indicator.className = 'flex items-center gap-2 flex-shrink-0 px-3.5 py-1.5 rounded-xl bg-moss-surface text-moss-dark border border-moss/40 font-hand font-bold text-base transition-all';
        if (badge) {
          badge.className = 'w-6 h-6 rounded-full bg-moss text-white font-sans text-xs font-bold flex items-center justify-center border border-charcoal';
          badge.innerText = '✓';
        }
      } else {
        indicator.className = 'flex items-center gap-2 flex-shrink-0 px-3 py-1.5 rounded-xl font-hand font-bold text-base transition-all text-charcoal/60';
        if (badge) {
          badge.className = 'w-6 h-6 rounded-full bg-charcoal/10 text-charcoal/70 font-sans text-xs font-bold flex items-center justify-center';
          badge.innerText = `${i}`;
        }
      }
    }

    const view = document.getElementById(`presStep${i}View`);
    if (view) view.style.display = i === stepNum ? 'block' : 'none';
  }

  const studio = document.getElementById('studio');
  if (studio) studio.scrollIntoView({ behavior: 'smooth' });
}

function escapePresentationHtml(value = '') {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function renderPresentationSlidePreview() {
  const previewBox = document.getElementById('presDeckPreview');
  const controls = document.getElementById('presSlidePreviewControls');
  const counter = document.getElementById('presPreviewCounter');
  const previous = document.getElementById('presPreviewPrevious');
  const next = document.getElementById('presPreviewNext');
  const slides = presentationPreviewDeck?.slides || [];
  if (!previewBox || !slides.length) return;

  presentationPreviewIndex = Math.max(0, Math.min(presentationPreviewIndex, slides.length - 1));
  const slide = slides[presentationPreviewIndex];
  const themeKey = presentationPreviewDeck.theme in PRESENTATION_PREVIEW_THEMES
    ? presentationPreviewDeck.theme
    : 'bold_tech';
  const theme = PRESENTATION_PREVIEW_THEMES[themeKey];
  const stickerFiles = PRESENTATION_PREVIEW_STICKERS[themeKey];
  const stickerUrls = stickerFiles.map(file => `${API_BASE}/decorative-assets/stickers/${file}`);
  const points = (slide.body_points || []).map(point => `<li>${escapePresentationHtml(point)}</li>`).join('');
  const cards = (slide.card_items || []).map(item => `
    <div style="background:${theme.surface}; border:1px solid ${theme.accent}; border-radius:12px; padding:14px; min-width:0;">
      <div style="font-weight:700; color:${theme.accent}; margin-bottom:4px;">${escapePresentationHtml(item.title || 'Insight')}</div>
      <div style="font-size:0.82rem; color:${theme.secondary};">${escapePresentationHtml(item.desc || '')}</div>
    </div>`).join('');
  const stat = slide.stat_number ? `
    <div style="margin:18px auto 0; max-width:380px; background:${theme.surface}; border:1px solid ${theme.accent}; border-radius:16px; padding:18px;">
      <div style="font-size:2.75rem; line-height:1; font-weight:800; color:${theme.accent};">${escapePresentationHtml(slide.stat_number)}</div>
      <div style="margin-top:7px; color:${theme.secondary}; font-size:0.9rem;">${escapePresentationHtml(slide.stat_label || '')}</div>
    </div>` : '';

  previewBox.className = 'border-2 border-charcoal rounded-xl overflow-hidden shadow-sketch-sm';
  previewBox.innerHTML = `
    <div class="relative aspect-[16/9] min-h-[260px] p-6 sm:p-10 flex flex-col justify-center text-left overflow-hidden" style="background:${theme.background}; color:${theme.primary};">
      <img src="${stickerUrls[0]}" alt="" aria-hidden="true" class="absolute right-4 top-3 w-14 sm:w-20 opacity-90 pointer-events-none" style="transform:rotate(8deg);">
      <img src="${stickerUrls[1]}" alt="" aria-hidden="true" class="absolute left-3 top-14 w-11 sm:w-16 opacity-90 pointer-events-none" style="transform:rotate(-11deg);">
      <img src="${stickerUrls[2]}" alt="" aria-hidden="true" class="absolute right-5 top-28 w-10 sm:w-14 opacity-85 pointer-events-none" style="transform:rotate(13deg);">
      <div class="font-hand text-xs font-bold uppercase tracking-widest mb-4" style="color:${theme.accent};">${escapePresentationHtml(presentationPreviewDeck.target_audience || 'General')} briefing</div>
      <h3 class="font-sketch text-2xl sm:text-4xl font-bold leading-tight" style="color:${theme.primary};">${escapePresentationHtml(slide.heading || `Slide ${presentationPreviewIndex + 1}`)}</h3>
      ${slide.subheading ? `<p class="font-hand text-base sm:text-lg mt-2" style="color:${theme.secondary};">${escapePresentationHtml(slide.subheading)}</p>` : ''}
      ${points ? `<ul class="font-hand text-sm sm:text-base mt-5 space-y-1 list-disc pl-5" style="color:${theme.primary};">${points}</ul>` : ''}
      ${cards ? `<div class="grid grid-cols-1 ${slide.card_items.length > 1 ? 'sm:grid-cols-2 lg:grid-cols-3' : ''} gap-3 mt-5">${cards}</div>` : ''}
      ${stat}
    </div>`;

  if (controls) controls.style.display = 'flex';
  if (counter) counter.textContent = `Slide ${presentationPreviewIndex + 1} of ${slides.length}`;
  if (previous) previous.disabled = presentationPreviewIndex === 0;
  if (next) {
    next.disabled = presentationPreviewIndex === slides.length - 1;
    next.textContent = presentationPreviewIndex === slides.length - 1 ? 'Last slide' : 'Next slide →';
  }
}

function changePresentationPreviewSlide(change) {
  if (!presentationPreviewDeck?.slides?.length) return;
  presentationPreviewIndex += change;
  renderPresentationSlidePreview();
}

function readPresentationField(container, field) {
  return container.querySelector(`[data-field="${field}"]`);
}

function syncPresentationDraftFromEditor() {
  if (!presentationDeckDraft) return;

  const title = document.getElementById('presDeckTitle');
  const subtitle = document.getElementById('presDeckSubtitle');
  const audience = document.getElementById('presDeckAudience');
  if (title) presentationDeckDraft.title = title.value.trim() || 'Untitled presentation';
  if (subtitle) presentationDeckDraft.subtitle = subtitle.value.trim();
  if (audience) presentationDeckDraft.target_audience = audience.value.trim() || 'General';

  document.querySelectorAll('[data-presentation-slide]').forEach((card) => {
    const slide = presentationDeckDraft.slides[Number(card.dataset.presentationSlide)];
    if (!slide) return;

    const layout = readPresentationField(card, 'layout');
    const heading = readPresentationField(card, 'heading');
    const subheading = readPresentationField(card, 'subheading');
    const bodyPoints = readPresentationField(card, 'body_points');
    const statNumber = readPresentationField(card, 'stat_number');
    const statLabel = readPresentationField(card, 'stat_label');
    const cardItems = readPresentationField(card, 'card_items');

    slide.layout = layout.value;
    slide.heading = heading.value.trim() || `Slide ${slide.idx}`;
    slide.subheading = subheading.value.trim() || null;
    slide.body_points = bodyPoints.value.split('\n').map(point => point.trim()).filter(Boolean);
    slide.stat_number = statNumber.value.trim() || null;
    slide.stat_label = statLabel.value.trim() || null;
    slide.card_items = cardItems.value.split('\n').map((line) => {
      const [itemTitle, ...description] = line.split('|');
      return { title: itemTitle.trim(), desc: description.join('|').trim() };
    }).filter(item => item.title || item.desc);
  });

  presentationDeckDraft.slides.forEach((slide, index) => { slide.idx = index + 1; });
}

function renderPresentationSlideEditors() {
  if (!presentationDeckDraft) return;

  const title = document.getElementById('presDeckTitle');
  const subtitle = document.getElementById('presDeckSubtitle');
  const audience = document.getElementById('presDeckAudience');
  const count = document.getElementById('presSlideCount');
  const editors = document.getElementById('presSlideEditors');
  if (!editors) return;

  if (title) title.value = presentationDeckDraft.title || '';
  if (subtitle) subtitle.value = presentationDeckDraft.subtitle || '';
  if (audience) audience.value = presentationDeckDraft.target_audience || 'General';
  if (count) count.textContent = presentationDeckDraft.slides.length;

  editors.innerHTML = presentationDeckDraft.slides.map((slide, index) => {
    const layoutOptions = PRESENTATION_LAYOUTS.map(([value, label]) => (
      `<option value="${value}" ${slide.layout === value ? 'selected' : ''}>${label}</option>`
    )).join('');
    const points = (slide.body_points || []).join('\n');
    const items = (slide.card_items || []).map(item => `${item.title || ''} | ${item.desc || ''}`).join('\n');

    return `
      <article data-presentation-slide="${index}" class="bg-white border-2 border-charcoal rounded-2xl p-5 shadow-sketch-sm">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <h4 class="font-sketch text-xl font-bold text-charcoal">Slide ${index + 1}</h4>
          <div class="flex items-center gap-2">
            <label class="font-hand text-sm font-bold">Layout
              <select data-field="layout" class="ml-1 p-1.5 bg-paper-tint border border-charcoal rounded-lg font-hand font-normal">${layoutOptions}</select>
            </label>
            <button type="button" class="px-3 py-1.5 bg-[#ffe8e2] border border-charcoal rounded-lg font-hand font-bold text-sm" onclick="removePresentationSlide(${index})">Remove</button>
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <label class="font-hand font-bold text-sm">Heading<input data-field="heading" value="${escapePresentationHtml(slide.heading)}" class="mt-1 w-full p-2 bg-paper-tint/40 border-2 border-charcoal rounded-xl font-hand font-normal"></label>
          <label class="font-hand font-bold text-sm">Subheading<input data-field="subheading" value="${escapePresentationHtml(slide.subheading || '')}" class="mt-1 w-full p-2 bg-paper-tint/40 border-2 border-charcoal rounded-xl font-hand font-normal"></label>
          <label class="font-hand font-bold text-sm md:col-span-2">Slide points <span class="font-normal text-charcoal/65">(one point per line)</span><textarea data-field="body_points" rows="3" class="mt-1 w-full p-2 bg-paper-tint/40 border-2 border-charcoal rounded-xl font-hand font-normal">${escapePresentationHtml(points)}</textarea></label>
          <label class="font-hand font-bold text-sm">Key stat <span class="font-normal text-charcoal/65">(optional)</span><input data-field="stat_number" value="${escapePresentationHtml(slide.stat_number || '')}" class="mt-1 w-full p-2 bg-paper-tint/40 border-2 border-charcoal rounded-xl font-hand font-normal"></label>
          <label class="font-hand font-bold text-sm">Stat label <span class="font-normal text-charcoal/65">(optional)</span><input data-field="stat_label" value="${escapePresentationHtml(slide.stat_label || '')}" class="mt-1 w-full p-2 bg-paper-tint/40 border-2 border-charcoal rounded-xl font-hand font-normal"></label>
          <label class="font-hand font-bold text-sm md:col-span-2">Cards or steps <span class="font-normal text-charcoal/65">(one per line: Title | description)</span><textarea data-field="card_items" rows="3" class="mt-1 w-full p-2 bg-paper-tint/40 border-2 border-charcoal rounded-xl font-hand font-normal">${escapePresentationHtml(items)}</textarea></label>
        </div>
      </article>`;
  }).join('');
}

async function createPresentationOutline() {
  const file = document.getElementById('presFileInput')?.files[0];
  const url = document.getElementById('presUrlInput')?.value.trim();
  const prompt = document.getElementById('presPromptInput')?.value.trim();
  const ingestStatus = document.getElementById('presIngestStatus');

  if (!file && !url && !prompt) {
    if (ingestStatus) ingestStatus.textContent = 'Add a file, URL, or topic to create the slide plan.';
    return;
  }

  const formData = new FormData();
  formData.append('theme', selectedPresentationTheme);
  if (file) formData.append('file', file);
  else if (url) formData.append('url', url);
  else formData.append('prompt', prompt);

  if (ingestStatus) ingestStatus.textContent = 'Analysing the source and planning your slides…';
  try {
    const response = await fetch(`${API_BASE}/api/presentation/plan`, { method: 'POST', body: formData });
    if (!response.ok) throw new Error(`Server returned ${response.status}`);

    presentationDeckDraft = await response.json();
    presentationDeckDraft.theme = selectedPresentationTheme;
    presentationDeckDraft.slides = presentationDeckDraft.slides || [];
    presentationDeckDraft.slides.forEach((slide, index) => { slide.idx = index + 1; });
    if (!presentationDeckDraft.slides.length) throw new Error('The source did not produce a usable slide plan.');

    renderPresentationSlideEditors();
    selectPresentationTheme(selectedPresentationTheme);
    document.getElementById('presDownloadGroup').style.display = 'none';
    if (ingestStatus) ingestStatus.textContent = `Draft ready: ${presentationDeckDraft.slides.length} proposed slides. Review and edit them below.`;
    goToPresentationStep(2);
  } catch (error) {
    if (ingestStatus) ingestStatus.textContent = `Could not create the slide plan: ${error.message}`;
  }
}

function addPresentationSlide() {
  syncPresentationDraftFromEditor();
  if (!presentationDeckDraft) return;
  presentationDeckDraft.slides.push({
    idx: presentationDeckDraft.slides.length + 1,
    layout: 'feature_cards',
    heading: 'New slide',
    subheading: '',
    body_points: [],
    stat_number: null,
    stat_label: null,
    card_items: []
  });
  renderPresentationSlideEditors();
}

function removePresentationSlide(index) {
  syncPresentationDraftFromEditor();
  if (!presentationDeckDraft || presentationDeckDraft.slides.length <= 1) {
    alert('A presentation needs at least one slide.');
    return;
  }
  presentationDeckDraft.slides.splice(index, 1);
  presentationDeckDraft.slides.forEach((slide, position) => { slide.idx = position + 1; });
  renderPresentationSlideEditors();
}

function selectPresentationTheme(theme) {
  selectedPresentationTheme = theme;
  if (presentationDeckDraft) presentationDeckDraft.theme = theme;
  document.querySelectorAll('[data-presentation-theme]').forEach((choice) => {
    const selected = choice.dataset.presentationTheme === theme;
    choice.style.outline = selected ? '3px solid #d97d64' : 'none';
    choice.style.transform = selected ? 'translateY(-2px)' : '';
    choice.setAttribute('aria-pressed', selected ? 'true' : 'false');
  });
}

function continueToPresentationDesign() {
  syncPresentationDraftFromEditor();
  if (!presentationDeckDraft || !presentationDeckDraft.slides.length) {
    alert('Create a slide plan before choosing the presentation style.');
    return;
  }
  goToPresentationStep(3);
}

async function renderApprovedPresentation() {
  syncPresentationDraftFromEditor();
  const statusText = document.getElementById('presStatusText');
  const previewBox = document.getElementById('presDeckPreview');
  if (!presentationDeckDraft || !presentationDeckDraft.slides.length) {
    if (statusText) statusText.textContent = 'Create and review a slide plan before rendering.';
    return;
  }

  presentationDeckDraft.theme = selectedPresentationTheme;
  if (statusText) statusText.textContent = 'Sending your approved slide content to the renderer…';
  if (previewBox) previewBox.innerHTML = '<div class="animate-spin text-3xl">⏳</div><div class="font-hand font-bold mt-2">Rendering your approved deck…</div>';
  goToPresentationStep(4);

  try {
    const response = await fetch(`${API_BASE}/api/presentation/jobs/from-script`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(presentationDeckDraft)
    });
    if (!response.ok) throw new Error(`Server returned ${response.status}`);
    const job = await response.json();
    pollReviewedPresentationJob(job.job_id);
  } catch (error) {
    goToPresentationStep(3);
    if (statusText) statusText.textContent = `Could not start the render: ${error.message}`;
    if (previewBox) previewBox.innerHTML = `<span class="text-red-600 font-bold">Presentation render failed: ${escapePresentationHtml(error.message)}</span>`;
  }
}

async function pollReviewedPresentationJob(jobId) {
  const statusText = document.getElementById('presStatusText');
  const previewBox = document.getElementById('presDeckPreview');
  const downloadGroup = document.getElementById('presDownloadGroup');
  const interval = setInterval(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/presentation/jobs/${jobId}`);
      if (!response.ok) throw new Error(`Server returned ${response.status}`);
      const job = await response.json();
      if (statusText) statusText.textContent = `Status: ${job.stage} (${job.progress}%)`;
      const stageLabel = document.getElementById('presStageLabel');
      const progressLabel = document.getElementById('presProgressPercent');
      const progressFill = document.getElementById('presProgressFill');
      if (stageLabel) stageLabel.textContent = job.stage || 'Rendering presentation…';
      if (progressLabel) progressLabel.textContent = `${job.progress || 0}%`;
      if (progressFill) progressFill.style.width = `${job.progress || 0}%`;

      if (job.status === 'done') {
        clearInterval(interval);
        const slides = job.script?.slides || presentationDeckDraft?.slides || [];
        goToPresentationStep(5);
        if (statusText) statusText.textContent = 'Presentation is ready to export.';
        presentationPreviewDeck = job.script || presentationDeckDraft;
        presentationPreviewIndex = 0;
        renderPresentationSlidePreview();
        if (downloadGroup) {
          downloadGroup.style.display = 'block';
          document.getElementById('btnPresDownloadHtml').href = `${API_BASE}/api/presentation/jobs/${jobId}/download?format=html_view`;
          document.getElementById('btnPresDownloadPdf').href = `${API_BASE}/api/presentation/jobs/${jobId}/download?format=pdf`;
          document.getElementById('btnPresDownloadPptx').href = `${API_BASE}/api/presentation/jobs/${jobId}/download?format=pptx`;
        }
      } else if (job.status === 'failed') {
        clearInterval(interval);
        goToPresentationStep(3);
        if (statusText) statusText.textContent = `Render failed: ${job.error || 'Unknown error'}`;
      }
    } catch (error) {
      clearInterval(interval);
      if (statusText) statusText.textContent = `Could not check render status: ${error.message}`;
    }
  }, 2000);
}

function restartPresentationWorkflow() {
  presentationDeckDraft = null;
  presentationPreviewDeck = null;
  presentationPreviewIndex = 0;
  selectedPresentationTheme = 'bold_tech';
  const fileInput = document.getElementById('presFileInput');
  const urlInput = document.getElementById('presUrlInput');
  const promptInput = document.getElementById('presPromptInput');
  const ingestStatus = document.getElementById('presIngestStatus');
  const downloadGroup = document.getElementById('presDownloadGroup');
  const previewControls = document.getElementById('presSlidePreviewControls');

  if (fileInput) fileInput.value = '';
  if (urlInput) urlInput.value = '';
  if (promptInput) promptInput.value = '';
  if (ingestStatus) ingestStatus.textContent = '';
  if (downloadGroup) downloadGroup.style.display = 'none';
  if (previewControls) previewControls.style.display = 'none';
  selectPresentationTheme(selectedPresentationTheme);
  goToPresentationStep(1);
}

function checkUrlParamsStudioMode() {
  const videoContainer = document.getElementById('videoStudioContainer');
  if (!videoContainer) return; // Not on studio.html page

  const urlParams = new URLSearchParams(window.location.search);
  const mode = urlParams.get('mode');
  if (!mode) {
    // A direct app entry belongs on the landing page, not inside a workflow.
    window.location.replace('index.html#hero');
    return;
  }
  
  openStudioMode(mode, urlParams.get('kind'));
}

function backToStudioChoice() {
  window.location.href = 'index.html#hero';
}

// ==========================================================
// Video Generation Studio Multi-Step Workflow
// ==========================================================

function selectVideoPlatform(platform) {
  currentPlatform = platform;
  const igBtn = document.getElementById('vPlatInstagram');
  const ytBtn = document.getElementById('vPlatYoutube');

  if (igBtn) {
    if (platform === 'instagram') {
      igBtn.className = 'px-3 py-1 rounded-full border-2 border-charcoal text-xs font-hand font-bold bg-moss-surface text-moss-dark shadow-sketch-sm';
    } else {
      igBtn.className = 'px-3 py-1 rounded-full border border-charcoal text-xs font-hand font-bold bg-white text-charcoal shadow-sketch-sm';
    }
  }

  if (ytBtn) {
    if (platform === 'youtube') {
      ytBtn.className = 'px-3 py-1 rounded-full border-2 border-charcoal text-xs font-hand font-bold bg-moss-surface text-moss-dark shadow-sketch-sm';
    } else {
      ytBtn.className = 'px-3 py-1 rounded-full border border-charcoal text-xs font-hand font-bold bg-white text-charcoal shadow-sketch-sm';
    }
  }

  showToast(`Platform set: ${platform.toUpperCase()}`);
}

// ================= MULTIMODAL INGESTION TAB HANDLERS =================
let currentInputMode = 'file'; // 'file', 'url', 'video', 'image', 'prompt'

function switchInputTab(mode) {
  currentInputMode = mode;
  const tabs = ['file', 'url', 'video', 'image', 'prompt'];

  tabs.forEach(t => {
    const btnName = `inputTabBtn${t.charAt(0).toUpperCase() + t.slice(1)}`;
    const paneName = `tabContent${t.charAt(0).toUpperCase() + t.slice(1)}`;
    const btn = document.getElementById(btnName);
    const pane = document.getElementById(paneName);

    if (btn) {
      if (t === mode) {
        btn.className = 'px-3 py-1.5 rounded-lg border border-charcoal bg-white shadow-sketch-sm text-charcoal flex items-center gap-1 transition-all active font-bold';
      } else {
        btn.className = 'px-3 py-1.5 rounded-lg border border-charcoal/30 bg-transparent text-charcoal/70 flex items-center gap-1 transition-all hover:bg-white font-bold';
      }
    }

    if (pane) {
      pane.style.display = (t === mode) ? 'block' : 'none';
    }
  });
}

async function handleUrlIngest() {
  const urlField = document.getElementById('inputUrlField');
  const url = urlField ? urlField.value.trim() : '';

  if (!url || !url.startsWith('http')) {
    showToast('⚠️ Please enter a valid URL (e.g. https://example.com/article)');
    return;
  }

  showToast('🌐 Fetching article from URL...');

  try {
    const res = await fetch(`${API_BASE}/api/video/ingest-url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'URL ingestion failed');
    }

    const docData = await res.json();
    showToast(`✅ URL Ingested: ${docData.char_count} chars extracted!`);

    const blob = new Blob([docData.text], { type: 'text/plain' });
    selectedFile = new File([blob], `article_${Date.now()}.txt`, { type: 'text/plain' });

    goToVideoStep2();
  } catch (err) {
    showToast(`❌ Error: ${err.message}`);
  }
}

async function handlePromptIngest() {
  const promptArea = document.getElementById('inputPromptArea');
  const promptText = promptArea ? promptArea.value.trim() : '';

  if (!promptText) {
    showToast('⚠️ Please enter a topic prompt or script instructions first!');
    return;
  }

  showToast('✍️ Synthesizing script outline from topic prompt...');

  try {
    const res = await fetch(`${API_BASE}/api/video/ingest-prompt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: promptText })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Prompt synthesis failed');
    }

    const docData = await res.json();
    showToast(`✨ Topic Script Synthesized!`);

    const blob = new Blob([docData.text], { type: 'text/plain' });
    selectedFile = new File([blob], `prompt_${Date.now()}.txt`, { type: 'text/plain' });

    goToVideoStep2();
  } catch (err) {
    showToast(`❌ Error: ${err.message}`);
  }
}

function handleMediaSelect(event, mediaType) {
  const file = event.target.files[0];
  if (!file) return;

  selectedFile = file;
  showToast(`📁 ${mediaType.toUpperCase()} file selected: ${file.name}`);
  goToVideoStep2();
}


function selectVideoCategory(category) {
  selectedVideoCategory = category;
  document.getElementById('typeShortForm').classList.toggle('selected', category === 'short');
  document.getElementById('typeLongForm').classList.toggle('selected', category === 'long');
  
  if (category === 'long') {
    document.getElementById('videoDurationInput').value = 180; // 3 minutes for long-form
    document.getElementById('aiDurationBadge').innerText = '180 seconds (3m)';
    selectVideoPlatform('youtube');
  } else {
    document.getElementById('videoDurationInput').value = 60; // 60s for short-form
    document.getElementById('aiDurationBadge').innerText = '60 seconds';
    selectVideoPlatform('instagram');
  }
  showToast(`Format category: ${category === 'short' ? 'Short Form Content (9:16)' : 'Long Form Content (16:9)'}`);
}

function goToVideoStep(stepNum) {
  // Update Stepper Bar Indicators
  for (let i = 1; i <= 5; i++) {
    const indicator = document.getElementById(`vStep${i}Indicator`);
    if (indicator) {
      const badge = indicator.querySelector('span:first-child');
      if (i === stepNum) {
        // Active step
        indicator.className = 'flex items-center gap-2 flex-shrink-0 px-3.5 py-1.5 rounded-xl bg-terracotta-soft text-terracotta border-2 border-charcoal font-hand font-bold text-base shadow-sketch-sm transition-all';
        if (badge) {
          badge.className = 'w-6 h-6 rounded-full bg-terracotta text-white font-sans text-xs font-bold flex items-center justify-center border border-charcoal';
          badge.innerText = `${i}`;
        }
      } else if (i < stepNum) {
        // Completed step
        indicator.className = 'flex items-center gap-2 flex-shrink-0 px-3.5 py-1.5 rounded-xl bg-moss-surface text-moss-dark border border-moss/40 font-hand font-bold text-base transition-all';
        if (badge) {
          badge.className = 'w-6 h-6 rounded-full bg-moss text-white font-sans text-xs font-bold flex items-center justify-center border border-charcoal';
          badge.innerText = '✓';
        }
      } else {
        // Upcoming step
        indicator.className = 'flex items-center gap-2 flex-shrink-0 px-3 py-1.5 rounded-xl font-hand font-bold text-base transition-all text-charcoal/60';
        if (badge) {
          badge.className = 'w-6 h-6 rounded-full bg-charcoal/10 text-charcoal/70 font-sans text-xs font-bold flex items-center justify-center';
          badge.innerText = `${i}`;
        }
      }
    }

    const view = document.getElementById(`videoStep${i}View`);
    if (view) {
      view.style.display = (i === stepNum) ? 'block' : 'none';
    }
  }

  const studio = document.getElementById('studio');
  if (studio) studio.scrollIntoView({ behavior: 'smooth' });
}

// Step 1 -> Step 2: Document Ingestion & AI Script Analysis
async function goToVideoStep2() {
  if (!selectedFile) {
    showToast('⚠️ Please provide a document, URL, video, image, or topic prompt first!');
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
    document.getElementById('ingestStatText').innerText = `Ingestion complete! ${numScenes} script beats distilled successfully.`;

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
  const container = document.getElementById('finalPlayerContainer');
  const formatSpec = document.getElementById('finalFormatSpec');

  const isLongForm = selectedVideoCategory === 'long';

  // Adapt player UI frame dynamically for 16:9 Widescreen vs 9:16 Vertical Reel
  if (container) {
    if (isLongForm) {
      container.className = 'relative w-full max-w-[560px] bg-charcoal rounded-[1.5rem] p-3 border-2 border-charcoal shadow-sketch-lg transition-all';
      if (player) player.className = 'w-full aspect-[16/9] rounded-[1rem] bg-black object-contain';
    } else {
      container.className = 'relative w-full max-w-[320px] bg-charcoal rounded-[2rem] p-3 border-2 border-charcoal shadow-sketch-lg transition-all';
      if (player) player.className = 'w-full aspect-[9/16] rounded-[1.5rem] bg-black object-cover';
    }
  }

  if (formatSpec) {
    formatSpec.innerHTML = isLongForm
      ? '• Format: <strong>1920 × 1080 (16:9 Widescreen Video)</strong>'
      : '• Format: <strong>1080 × 1920 (9:16 Vertical Reel)</strong>';
  }

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
  const dropTitle = document.getElementById('dropTitle');
  const dropSubtitle = document.getElementById('dropSubtitle');
  if (dropTitle) {
    dropTitle.innerText = `📄 ${file.name}`;
  }
  if (dropSubtitle) {
    dropSubtitle.innerText = `${(file.size / 1024 / 1024).toFixed(2)} MB • Ready for Ingestion & Script Analysis`;
  }
  const dropzone = document.getElementById('dropzone');
  if (dropzone) {
    dropzone.style.borderColor = '#728c69';
    dropzone.style.backgroundColor = '#eef4ec';
  }
  showToast(`Loaded document: ${file.name}`);
}

function loadSampleDoc() {
  const content = `# Local AI Desktop Browser - Architecture Whitepaper\n\nExecutive Briefing:\nMost local AI solutions fail to bridge the gap between heavy neural compute and intuitive desktop UI.\nPostEazy translates structured whitepapers, slides, and docs directly into 60 FPS kinetic watercolor video reels.\n\nKey Finding 01: 42% growth in content engagement when using kinetic typography.\nKey Finding 02: Faceless automated workflows cut production overhead by 90%.`;
  const file = new File([content], "Sample_AI_Whitepaper.txt", { type: "text/plain" });
  setFile(file);
}

function clearFile(event) {
  if (event) event.stopPropagation();
  selectedFile = null;
  const fileInput = document.getElementById('fileInput');
  if (fileInput) fileInput.value = '';
  const dropTitle = document.getElementById('dropTitle');
  const dropSubtitle = document.getElementById('dropSubtitle');
  if (dropTitle) dropTitle.innerText = 'Click or drag & drop document';
  if (dropSubtitle) dropSubtitle.innerText = 'Upload papers, decks, or write-ups up to 25MB for parsing';
  const dropzone = document.getElementById('dropzone');
  if (dropzone) {
    dropzone.style.borderColor = '';
    dropzone.style.backgroundColor = '';
  }
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

// ================= CINEMATIC SCROLL HERO SEQUENCE (NO DECORATIVE UI) =================
const TOTAL_CINEMATIC_FRAMES = 145;
const frameImages = [];
let framesLoadedCount = 0;
let isFrameSequenceReady = false;

// Preload WebP frame sequence into memory for 0ms latency 60fps canvas scrubbing
function preloadCinematicFrames() {
  for (let i = 1; i <= TOTAL_CINEMATIC_FRAMES; i++) {
    const img = new Image();
    const frameNum = String(i).padStart(3, '0');
    img.src = `media/frames/frame_${frameNum}.webp`;
    img.onload = () => {
      framesLoadedCount++;
      if (framesLoadedCount >= 10) {
        isFrameSequenceReady = true;
      }
    };
    frameImages.push(img);
  }
}

function initCinematicHeroScroll() {
  preloadCinematicFrames();

  const runway = document.getElementById('hero-runway');
  const canvas = document.getElementById('cinematicHeroCanvas');
  const video = document.getElementById('heroCinematicVideo');
  const typography = document.getElementById('heroCinematicTypography');

  if (!runway || !canvas) return;

  const ctx = canvas.getContext('2d');

  let currentFrameFloat = 0;
  let targetFrameFloat = 0;
  let targetVideoTime = 0;
  let currentVideoTime = 0;
  let videoDuration = 6.04;
  let isVideoMetadataLoaded = false;
  let animationFrameId = null;

  if (video) {
    video.addEventListener('loadedmetadata', () => {
      videoDuration = video.duration || 6.04;
      isVideoMetadataLoaded = true;
    });
  }

  // Handle High-DPI Canvas Resizing with Object-Fit Cover scaling (NO BLACK BARS!)
  function resizeCanvas() {
    const dpr = window.devicePixelRatio || 1;
    const width = window.innerWidth;
    const height = window.innerHeight;

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';

    ctx.scale(dpr, dpr);
    renderCurrentFrame();
  }

  window.addEventListener('resize', resizeCanvas);

  function drawImageObjectFitCover(imgSource) {
    if (!imgSource) return;

    const width = window.innerWidth;
    const height = window.innerHeight;

    const imgWidth = imgSource.videoWidth || imgSource.width || 752;
    const imgHeight = imgSource.videoHeight || imgSource.height || 416;

    if (!imgWidth || !imgHeight) return;

    const imgAspect = imgWidth / imgHeight;
    const canvasAspect = width / height;

    let renderW, renderH, renderX, renderY;

    if (canvasAspect > imgAspect) {
      renderW = width;
      renderH = width / imgAspect;
      renderX = 0;
      renderY = (height - renderH) / 2;
    } else {
      renderH = height;
      renderW = height * imgAspect;
      renderX = (width - renderW) / 2;
      renderY = 0;
    }

    ctx.clearRect(0, 0, width, height);
    ctx.drawImage(imgSource, renderX, renderY, renderW, renderH);
  }

  function renderCurrentFrame() {
    const frameIndex = Math.min(
      TOTAL_CINEMATIC_FRAMES - 1,
      Math.max(0, Math.round(currentFrameFloat))
    );

    if (frameImages[frameIndex] && frameImages[frameIndex].complete) {
      drawImageObjectFitCover(frameImages[frameIndex]);
    } else if (frameImages[0] && frameImages[0].complete) {
      drawImageObjectFitCover(frameImages[0]);
    } else if (video && video.readyState >= 2) {
      drawImageObjectFitCover(video);
    }
  }

  // Smooth lerp loop running via requestAnimationFrame
  function animLoop() {
    const runwayRect = runway.getBoundingClientRect();
    const scrollDistance = runway.offsetHeight - window.innerHeight;

    if (scrollDistance > 0) {
      let progress = -runwayRect.top / scrollDistance;
      progress = Math.max(0, Math.min(1, progress));

      // Calculate Target Frame / Video Time
      targetFrameFloat = progress * (TOTAL_CINEMATIC_FRAMES - 1);
      targetVideoTime = progress * videoDuration;

      // Smooth lerp interpolation for silky motion (forward AND rewind)
      currentFrameFloat += (targetFrameFloat - currentFrameFloat) * 0.18;
      currentVideoTime += (targetVideoTime - currentVideoTime) * 0.18;

      // Video currentTime scrubbing fallback
      if (video && isVideoMetadataLoaded && Math.abs(video.currentTime - currentVideoTime) > 0.04) {
        try {
          video.currentTime = currentVideoTime;
        } catch (e) {}
      }

      // Render Frame to Canvas
      renderCurrentFrame();

      // Typography animation: subtly moves, scales down, and fades as scroll progresses
      if (typography) {
        if (progress <= 0.25) {
          const fadeRatio = progress / 0.25;
          const opacity = Math.max(0, 1 - fadeRatio);
          const translateY = -progress * 140;
          const scale = 1 - progress * 0.15;
          typography.style.opacity = opacity.toFixed(3);
          typography.style.transform = `translateY(${translateY.toFixed(1)}px) scale(${scale.toFixed(3)})`;
        } else {
          typography.style.opacity = '0';
        }
      }
    }

    animationFrameId = requestAnimationFrame(animLoop);
  }

  resizeCanvas();
  animLoop();
}
