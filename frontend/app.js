/**
 * DineAI — app.js
 * Phase 7 Frontend JavaScript
 * Handles: view transitions, form logic, API calls, dynamic rendering
 */

'use strict';

// ================================================================
// 1. CONSTANTS & CONFIG
// ================================================================
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
  ? 'http://localhost:8000' 
  : 'https://your-app.up.railway.app'; // <--- Replace with your actual Railway URL

const API_ENDPOINT = `${API_BASE}/recommend`;

// ================================================================
// 2. DOM REFERENCES
// ================================================================
const views = {
  home:        document.getElementById('view-home'),
  preferences: document.getElementById('view-preferences'),
  processing:  document.getElementById('view-processing'),
  results:     document.getElementById('view-results'),
};

// Nav
const navLinks = document.querySelectorAll('.nav-link[data-view]');
const navCTA   = document.getElementById('nav-cta');
const brandLogo = document.getElementById('brand-logo');

// Home
const heroSearchBtn   = document.getElementById('hero-search-btn');
const heroSearchInput = document.getElementById('hero-search-input');

// Form
const prefForm     = document.getElementById('preferenceForm');
const locationSel  = document.getElementById('location');
const budgetHidden = document.getElementById('budget');
const cuisineHidden = document.getElementById('cuisine');
const ratingSlider = document.getElementById('min_rating');
const ratingVal    = document.getElementById('ratingVal');
const extrasTA     = document.getElementById('extras');
const submitBtn    = document.getElementById('submit-btn');
const formError    = document.getElementById('form-error');

// Budget
const budgetBtns      = document.querySelectorAll('.budget-btn');
const budgetIndicator = document.getElementById('budgetIndicator');

// Cuisine chips
const cuisineChips = document.querySelectorAll('.chip[data-cuisine]');

// Processing
const processingMsgs = document.querySelectorAll('.msg');

// Results
const resultsList    = document.getElementById('results-list');
const resultsError   = document.getElementById('results-error');
const resultsSubtitle = document.getElementById('results-subtitle');
const errorBodyText  = document.getElementById('error-body-text');
const tryAgainBtn    = document.getElementById('try-again-btn');
const refineBtn      = document.getElementById('refine-btn');
const refineCta      = document.getElementById('refine-cta');

// ================================================================
// 3. STATE
// ================================================================
let currentView = 'home';
let selectedBudget  = 'low';
let selectedCuisines = [];
let msgCycleTimer = null;
let currentMsgIndex = 0;

// ================================================================
// 4. VIEW TRANSITIONS
// ================================================================
function showView(name) {
  if (!views[name]) return;
  // Guard: if already on this view (e.g., initial load), just ensure it's visible
  if (currentView === name) {
    const v = views[name];
    v.classList.add('active');
    v.style.opacity = '1';
    v.style.transform = 'translateY(0)';
    return;
  }

  // Hide current view
  const prevView = views[currentView];
  if (prevView) {
    prevView.style.opacity = '0';
    prevView.style.transform = 'translateY(12px)';
    setTimeout(() => {
      prevView.classList.remove('active');
      prevView.style.opacity = '';
      prevView.style.transform = '';
    }, 280);
  }

  currentView = name;

  // Show new view
  const nextView = views[name];
  nextView.style.opacity = '0';
  nextView.style.transform = 'translateY(12px)';
  nextView.classList.add('active');
  // Let the browser paint the flex layout before animating
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      nextView.style.opacity = '1';
      nextView.style.transform = 'translateY(0)';
    });
  });

  // Update nav active state
  navLinks.forEach(link => {
    link.classList.toggle('active', link.dataset.view === name);
  });

  // Scroll to top
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ================================================================
// 5. PARTICLE CANVAS (Home hero atmosphere)
// ================================================================
function initParticles() {
  const wrap = document.getElementById('particles-canvas-wrap');
  if (!wrap) return;

  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  wrap.appendChild(canvas);

  function resize() {
    canvas.width  = wrap.offsetWidth;
    canvas.height = wrap.offsetHeight;
  }
  window.addEventListener('resize', resize);
  resize();

  class Particle {
    constructor() { this.reset(); }
    reset() {
      this.x     = Math.random() * canvas.width;
      this.y     = Math.random() * canvas.height;
      this.size  = Math.random() * 1.8 + 0.4;
      this.vx    = (Math.random() - 0.5) * 0.4;
      this.vy    = (Math.random() - 0.5) * 0.4;
      this.alpha = Math.random() * 0.6 + 0.2;
      this.color = Math.random() > 0.5 ? '#F59E0B' : '#04b4a2';
    }
    update() {
      this.x += this.vx;
      this.y += this.vy;
      if (this.x > canvas.width)  this.x = 0;
      if (this.x < 0)             this.x = canvas.width;
      if (this.y > canvas.height) this.y = 0;
      if (this.y < 0)             this.y = canvas.height;
    }
    draw() {
      ctx.globalAlpha = this.alpha;
      ctx.fillStyle   = this.color;
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  const particles = Array.from({ length: 60 }, () => new Particle());

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.globalAlpha = 1;
    particles.forEach(p => { p.update(); p.draw(); });
    requestAnimationFrame(animate);
  }
  animate();
}

// ================================================================
// 6. BUDGET TOGGLE
// ================================================================
function selectBudget(index, value) {
  selectedBudget = value;
  budgetHidden.value = value;

  // Move indicator
  const pct = index * 33.333;
  budgetIndicator.style.left = `calc(${pct}% + 4px)`;

  // Update button states
  budgetBtns.forEach((btn, i) => {
    const isActive = i === index;
    btn.classList.toggle('active', isActive);
    btn.setAttribute('aria-pressed', String(isActive));
  });
}

function initBudgetToggle() {
  budgetBtns.forEach((btn, index) => {
    btn.addEventListener('click', () => {
      selectBudget(index, btn.dataset.budget);
    });
  });
  // Initialize
  selectBudget(0, 'low');
}

// ================================================================
// 7. CUISINE CHIPS
// ================================================================
function initCuisineChips() {
  cuisineChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const cuisine = chip.dataset.cuisine;
      const isActive = chip.classList.toggle('active');
      chip.setAttribute('aria-pressed', String(isActive));

      if (isActive) {
        if (!selectedCuisines.includes(cuisine)) selectedCuisines.push(cuisine);
      } else {
        selectedCuisines = selectedCuisines.filter(c => c !== cuisine);
      }
      cuisineHidden.value = selectedCuisines.join(',');
    });
  });
}

// ================================================================
// 8. RATING SLIDER
// ================================================================
function initRatingSlider() {
  ratingSlider.addEventListener('input', () => {
    const v = parseFloat(ratingSlider.value).toFixed(1);
    ratingVal.textContent = v;
    ratingSlider.setAttribute('aria-valuenow', v);
  });
}

// ================================================================
// 9. HERO SEARCH → PRE-FILL FORM
// ================================================================
function initHeroSearch() {
  function go() {
    const query = heroSearchInput.value.trim();
    // Pre-fill extras if user typed something
    if (query && extrasTA) {
      extrasTA.value = query;
    }
    showView('preferences');
  }

  heroSearchBtn.addEventListener('click', go);
  heroSearchInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') go();
  });
}

// ================================================================
// 10. PROCESSING MESSAGE CYCLE
// ================================================================
function startMsgCycle() {
  currentMsgIndex = 0;
  processingMsgs.forEach(m => m.classList.remove('active'));
  processingMsgs[0]?.classList.add('active');

  msgCycleTimer = setInterval(() => {
    processingMsgs[currentMsgIndex]?.classList.remove('active');
    currentMsgIndex = (currentMsgIndex + 1) % processingMsgs.length;
    processingMsgs[currentMsgIndex]?.classList.add('active');
  }, 2200);
}

function stopMsgCycle() {
  clearInterval(msgCycleTimer);
  processingMsgs.forEach(m => m.classList.remove('active'));
}

// ================================================================
// 11. FORM VALIDATION
// ================================================================
function validateForm() {
  const location = locationSel.value;
  if (!location) {
    showFormError('Please select a location to continue.');
    return false;
  }
  hideFormError();
  return true;
}

function showFormError(msg) {
  formError.textContent = msg;
  formError.classList.remove('hidden');
}
function hideFormError() {
  formError.classList.add('hidden');
  formError.textContent = '';
}

// ================================================================
// 12. API CALL
// ================================================================
async function fetchRecommendations(payload) {
  const response = await fetch(API_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let detail = `Server error (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) detail = err.detail;
    } catch (_) { /* ignore */ }
    throw new Error(detail);
  }

  return response.json();
}

// ================================================================
// 13. FORM SUBMIT HANDLER
// ================================================================
function initForm() {
  prefForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    // Build payload
    const payload = {
      location:   locationSel.value,
      budget:     selectedBudget,
      cuisine:    selectedCuisines.join(','),   // all selected chips, comma-joined ('' if none)
      min_rating: parseFloat(ratingSlider.value),
      extras:     extrasTA.value.trim(),
    };

    // Show processing screen
    showView('processing');
    startMsgCycle();

    submitBtn.disabled = true;

    try {
      const data = await fetchRecommendations(payload);
      stopMsgCycle();
      renderResults(data, payload);
      showView('results');
    } catch (err) {
      stopMsgCycle();
      renderError(err.message);
      showView('results');
    } finally {
      submitBtn.disabled = false;
    }
  });
}

// ================================================================
// 14. RENDER HELPERS
// ================================================================

/** Generate star icon HTML */
function starIcon(filled = true) {
  const fill = filled ? 'FILL' : '0';
  return `<span class="material-symbols-outlined star-icon" style="font-variation-settings:'FILL' ${filled ? 1 : 0}">star</span>`;
}

/** Build star rating display (0–5 scale, show up to 5 stars) */
function buildStars(rating) {
  const full  = Math.floor(rating);
  const hasHalf = (rating % 1) >= 0.5;
  const empty = 5 - full - (hasHalf ? 1 : 0);
  let html = '';
  for (let i = 0; i < full;  i++) html += starIcon(true);
  if (hasHalf)                     html += `<span class="material-symbols-outlined star-icon" style="font-variation-settings:'FILL' 0">star_half</span>`;
  for (let i = 0; i < empty; i++) html += `<span class="material-symbols-outlined star-icon" style="font-variation-settings:'FILL' 0;opacity:0.3">star</span>`;
  return html;
}

/** Parse cuisine string → array of tags */
function parseCuisines(cuisineStr) {
  if (!cuisineStr) return [];
  return cuisineStr
    .split(/[,\/&]/)
    .map(s => s.trim())
    .filter(Boolean)
    .slice(0, 3);
}

/** Render a single restaurant card */
function buildCardHTML(rec, index) {
  const cuisines = parseCuisines(rec.cuisine);
  const cuisineTags = cuisines.map(c =>
    `<span class="cuisine-tag">${escapeHTML(c)}</span>`
  ).join('');

  const rankClass = index === 0 ? 'rank-1' : '';
  const isTopPick = index === 0;

  // Color-coded gradient pattern
  const gradientColors = [
    'linear-gradient(135deg, rgba(245,158,11,0.18), rgba(4,180,162,0.08))',
    'linear-gradient(135deg, rgba(4,180,162,0.15), rgba(245,158,11,0.06))',
    'linear-gradient(135deg, rgba(255,189,168,0.12), rgba(245,158,11,0.08))',
  ];
  const cardAccent = gradientColors[index % gradientColors.length];

  return `
    <article class="restaurant-card" style="animation-delay: ${index * 0.12}s;" aria-label="Restaurant recommendation ${index + 1}: ${escapeHTML(rec.name)}">
      <!-- Color accent strip -->
      <div style="height:3px;background:${cardAccent};"></div>

      <div class="card-content">
        <!-- Top row -->
        <div class="card-top">
          <div class="card-header-left">
            <div class="rank-badge-inline ${rankClass}" aria-label="Rank ${rec.rank}">${rec.rank}</div>
            <h2 class="card-name">${escapeHTML(rec.name)}</h2>
            <div class="card-tags">${cuisineTags}${isTopPick ? '<span class="cuisine-tag" style="color:var(--primary);border-color:var(--primary-container);background:rgba(245,158,11,0.10)">Top Pick</span>' : ''}</div>
          </div>
          <button class="card-bookmark" aria-label="Save ${escapeHTML(rec.name)}">
            <span class="material-symbols-outlined">bookmark_border</span>
          </button>
        </div>

        <!-- Meta row -->
        <div class="card-meta">
          <div class="meta-item">
            <span class="material-symbols-outlined star-icon">star</span>
            <span class="meta-rating-val">${rec.rating.toFixed(1)}</span>
            <span>/ 5.0</span>
          </div>
          <div class="meta-dot" aria-hidden="true"></div>
          <div class="meta-item">
            <span class="material-symbols-outlined">payments</span>
            <span>${escapeHTML(rec.estimated_cost)}</span>
          </div>
        </div>

        <!-- AI Explanation -->
        <div class="ai-explanation">
          <div class="ai-explanation-pulse" aria-hidden="true"></div>
          <div class="ai-explanation-inner">
            <div class="ai-body">
              <span class="material-symbols-outlined ai-icon">psychology</span>
              <p class="ai-text">"${escapeHTML(rec.explanation)}"</p>
            </div>
            ${rec.explanation.length > 80 ? `
            <button class="why-toggle" aria-expanded="false" aria-controls="why-${index}">
              <span>Why this match?</span>
              <span class="material-symbols-outlined why-chevron">expand_more</span>
            </button>
            <div class="why-content" id="why-${index}" role="region" aria-label="Detailed reason">
              <div class="why-inner">
                This restaurant was ranked based on a contextual analysis of your preferences, including cuisine affinity, budget alignment, and location proximity. Our AI evaluated sentiment from recent diner reviews and weighted authenticity markers to surface this recommendation.
              </div>
            </div>` : ''}
          </div>
        </div>
      </div>
    </article>
  `;
}

/** Render all results */
function renderResults(data, payload) {
  resultsList.innerHTML = '';
  resultsError.classList.add('hidden');
  refineCta.classList.remove('hidden');

  const recs = data.recommendations || [];

  if (recs.length === 0) {
    renderError('No restaurants matched your preferences. Try adjusting your filters.');
    return;
  }

  // Update subtitle
  const locationLabel = locationSel.options[locationSel.selectedIndex]?.text || payload.location;
  resultsSubtitle.textContent = `Found ${data.total_found} restaurants in ${locationLabel} — here are your top AI-curated picks.`;

  // Build cards
  resultsList.innerHTML = recs.map((rec, i) => buildCardHTML(rec, i)).join('');

  // Attach toggle handlers
  document.querySelectorAll('.why-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const content = btn.nextElementSibling;
      const chevron = btn.querySelector('.why-chevron');
      const isOpen = content.classList.toggle('open');
      chevron.classList.toggle('open', isOpen);
      btn.setAttribute('aria-expanded', String(isOpen));
    });
  });

  // Bookmark toggle (UI only — persistence not implemented)
  document.querySelectorAll('.card-bookmark').forEach(btn => {
    btn.addEventListener('click', () => {
      const icon = btn.querySelector('.material-symbols-outlined');
      const isSaved = icon.textContent === 'bookmark';
      icon.textContent = isSaved ? 'bookmark_border' : 'bookmark';
      icon.style.color  = isSaved ? '' : 'var(--primary)';
    });
  });
}

/** Render error state */
function renderError(message) {
  resultsList.innerHTML = '';
  refineCta.classList.add('hidden');
  errorBodyText.textContent = message || 'Something went wrong. Please try again.';
  resultsError.classList.remove('hidden');
}

// ================================================================
// 15. UTILITY
// ================================================================
function escapeHTML(str) {
  if (typeof str !== 'string') return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ================================================================
// 16. NAV / ROUTING
// ================================================================
function initNav() {
  // Nav links
  navLinks.forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      showView(link.dataset.view);
    });
  });

  // CTA button → preferences
  navCTA.addEventListener('click', () => showView('preferences'));

  // Brand logo → home
  brandLogo.addEventListener('click', e => {
    e.preventDefault();
    showView('home');
  });

  // Try again / refine
  tryAgainBtn?.addEventListener('click', () => showView('preferences'));
  refineBtn?.addEventListener('click', () => showView('preferences'));
}

// ================================================================
// 17. INIT
// ================================================================
document.addEventListener('DOMContentLoaded', () => {
  initParticles();
  initBudgetToggle();
  initCuisineChips();
  initRatingSlider();
  initHeroSearch();
  initForm();
  initNav();

  // Force initial view to render correctly
  showView('home');
});
