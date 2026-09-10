// Project Jericho — 3D XYZ Component Breakdown & Assembly Engine
// Continuous 4-scene connected spatial journey:
// Scene 01: Familiar by design (starts assembled)
// Scene 02: 3D Spatial Breakdown (explodes into deep Z-space, no labels, no HUD pins)
// Scene 03: Precision 3D Assembly (parts converge, temple docks flush, lens sensor disappears)
// Scene 04: Seamlessly United (rotates straight, seamlessly zooms out to single frame)

const header        = document.querySelector('[data-header]');
const menuBtn       = document.querySelector('[data-menu-button]');
const nav           = document.querySelector('[data-nav]');
const pgBar         = document.querySelector('.scroll-progress span');

const storyLayout   = document.querySelector('.story-layout');
const storyStage    = document.querySelector('[data-story-stage]');
const storySteps    = [...document.querySelectorAll('[data-story-step]')];
const stageNum      = document.querySelector('[data-stage-number]');
const stageLbl      = document.querySelector('[data-stage-label]');
const stageProg     = document.querySelector('[data-stage-progress]');

const canvas        = document.querySelector('.breakdown-canvas');
const canvasWrap    = document.querySelector('.canvas-stage-wrap');
const cornerLight   = document.querySelector('.corner-camera-light');
const dockGlint     = document.querySelector('.hinge-dock-glint');
const straightGlow  = document.querySelector('.straight-glow');

// Top-right corner frame coordinates [left%, top%] across 72 frames
const CORNER_COORDS = [
  null,
  [56.48, 44.02], [56.82, 44.17], [57.17, 44.32], [57.51, 44.47], [57.86, 44.63],
  [58.20, 44.79], [58.54, 44.95], [58.89, 45.11], [59.23, 45.27], [59.58, 45.43],
  [59.92, 45.59], [60.26, 45.75], [60.61, 45.91], [60.95, 46.06], [61.30, 46.22],
  [61.64, 46.37], [61.99, 46.52], [62.34, 46.67], [62.69, 46.82], [63.04, 46.96],
  [63.38, 47.10], [63.74, 47.23], [64.09, 47.36], [64.44, 47.48], [64.79, 47.60],
  [65.15, 47.71], [65.50, 47.82], [65.86, 47.92], [66.21, 48.02], [66.57, 48.11],
  [66.93, 48.19], [67.28, 48.27], [67.65, 48.15], [68.01, 48.03], [68.38, 47.91],
  [68.75, 47.79], [69.11, 47.67], [69.48, 47.54], [69.85, 47.41], [70.22, 47.27],
  [70.58, 47.13], [70.95, 46.99], [71.32, 46.85], [71.69, 46.70], [72.05, 46.55],
  [72.42, 46.39], [72.78, 46.23], [73.15, 46.07], [73.51, 45.90], [73.87, 45.73],
  [74.23, 45.56], [74.58, 45.38], [74.94, 45.20], [75.29, 45.01], [75.64, 44.82],
  [75.98, 44.62], [76.33, 44.43], [76.67, 44.23], [77.00, 44.02], [77.33, 43.81],
  [77.66, 43.60], [77.98, 43.38], [78.30, 43.16], [78.61, 42.94], [78.92, 42.71],
  [79.22, 42.48], [79.52, 42.25], [79.81, 42.01], [80.10, 41.77], [80.37, 41.53],
  [80.64, 41.29], [80.91, 41.04]
];

// Multi-angle layers & breakdown group
const layerSide     = document.querySelector('.angle-layer-side');
const layerNear     = document.querySelector('.angle-layer-near');
const layerFront    = document.querySelector('.angle-layer-front');
const partsWrap     = document.querySelector('.breakdown-parts-wrap');

// 3D Component wraps
const partFrame     = document.querySelector('.part-wrap-frame');
const partSensor    = document.querySelector('.part-wrap-sensor');
const partTemple    = document.querySelector('.part-wrap-temple');
const partSpeaker   = document.querySelector('.part-wrap-speaker');
const partBattery   = document.querySelector('.part-wrap-battery');
const partNpu       = document.querySelector('.part-wrap-npu');
const partCable     = document.querySelector('.part-wrap-cable');

// ── Lerp & Cursor Parallax State ──────────────────────────────────────────────
let curP = 0, tgtP = 0, ticking = false;
let mouseX = 0.5, mouseY = 0.5;
let curTiltX = 0, curTiltY = 0;

// ── Easing Utilities ──────────────────────────────────────────────────────────
const easeIO = x => x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const easeO3 = x => 1 - Math.pow(1 - x, 3);
const easeI2 = x => x * x;
function clamp(v, a, b) { return Math.min(Math.max(v, a), b); }
function range(p, a, b, fn) {
  const t = clamp((p - a) / (b - a), 0, 1);
  return fn ? fn(t) : t;
}

// ── Header & Scroll Progress ──────────────────────────────────────────────────
function chrome() {
  const y = window.scrollY;
  header?.classList.toggle('is-scrolled', y > 24);
  const max = document.documentElement.scrollHeight - window.innerHeight;
  if (pgBar) pgBar.style.transform = `scaleX(${max > 0 ? clamp(y / max, 0, 1) : 0})`;
  updateQuickNav();
}

// ── Mobile Menu ───────────────────────────────────────────────────────────────
menuBtn?.addEventListener('click', () => {
  const o = menuBtn.getAttribute('aria-expanded') === 'true';
  menuBtn.setAttribute('aria-expanded', String(!o));
  nav?.classList.toggle('is-open', !o);
  document.body.classList.toggle('menu-open', !o);
});
nav?.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
  menuBtn?.setAttribute('aria-expanded', 'false');
  nav.classList.remove('is-open');
  document.body.classList.remove('menu-open');
}));

// ── Quick Section Navigation ──────────────────────────────────────────────────
const quickNav = document.querySelector('[data-quick-nav]');
const quickPills = quickNav ? [...quickNav.querySelectorAll('.quick-pill')] : [];
const quickSections = quickPills.map(p => {
  const id = p.getAttribute('href');
  return id ? document.querySelector(id) : null;
}).filter(Boolean);

function updateQuickNav() {
  if (!quickPills.length || !quickSections.length) return;
  const headerH = header ? header.offsetHeight : 68;
  const quickH = quickNav ? quickNav.offsetHeight : 42;
  const scrollPos = window.scrollY + headerH + quickH + 60;

  let activeIdx = 0;
  for (let i = 0; i < quickSections.length; i++) {
    if (quickSections[i].offsetTop <= scrollPos) {
      activeIdx = i;
    }
  }

  quickPills.forEach((p, idx) => {
    const isAct = idx === activeIdx;
    if (p.classList.contains('is-active') !== isAct) {
      p.classList.toggle('is-active', isAct);
      if (isAct) {
        p.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
      }
    }
  });
}

quickPills.forEach(p => {
  p.addEventListener('click', e => {
    const id = p.getAttribute('href');
    const target = id ? document.querySelector(id) : null;
    if (target) {
      e.preventDefault();
      const headerH = header ? header.offsetHeight : 68;
      const quickH = quickNav ? quickNav.offsetHeight : 42;
      const targetY = target.getBoundingClientRect().top + window.scrollY - headerH - quickH + 4;
      window.scrollTo({ top: Math.max(0, targetY), behavior: 'smooth' });
    }
  });
});

// ── Reveal Observer ───────────────────────────────────────────────────────────
const ro = new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) { e.target.classList.add('is-visible'); ro.unobserve(e.target); }
}), { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
document.querySelectorAll('.reveal').forEach(el => ro.observe(el));

// ── Story Steps Indicator ─────────────────────────────────────────────────────
function setStep(i) {
  if (!storyStage) return;
  storyStage.className = storyStage.className.replace(/state-\d+/g, '').trim() + ` state-${i}`;
  storySteps.forEach(s => s.classList.toggle('is-active', +s.dataset.storyStep === i));
  const a = storySteps.find(s => +s.dataset.storyStep === i);
  if (stageNum) stageNum.textContent = String(i + 1).padStart(2, '0');
  if (stageLbl && a) stageLbl.textContent = a.dataset.label || '';
  if (stageProg) stageProg.style.width = `${((i + 1) / storySteps.length) * 100}%`;
}

// ── Responsive Scale Factor ───────────────────────────────────────────────────
function getScaleFactor() {
  if (!canvas) return 0.5;
  const w = canvas.offsetWidth;
  return w > 0 ? w / 1800 : 0.5;
}

// ══════════════════════════════════════════════════════════════════════════════
// ══════════════════════════════════════════════════════════════════════════════
//  MOTION AI KIT: SPRING PHYSICS ENGINE (stiffness: 140, damping: 26)
//  Critically damped, ultra-responsive inertial scrubber with zero stutter
// ══════════════════════════════════════════════════════════════════════════════
const SPRING = {
  stiffness: 140,
  damping: 26,
  mass: 1.0,
  restDelta: 0.0001,
  restSpeed: 0.0001
};

let springPos = 0;
let springVel = 0;
let lastFrameTime = performance.now();

// ══════════════════════════════════════════════════════════════════════════════
//  3D BLENDER RENDER ENGINE: 72-FRAME HIGH-DENSITY SCRUBBER (2x FRAME RATE)
//  Sequence across 72 frames:
//    Frames 01-10: Sideways hero profile (Familiar by design)
//    Frames 11-34: 3D Component breakdown explosion (Intelligence within)
//    Frames 35-46: Reassembly flush docking (Technology recedes)
//    Frames 47-72: Continuous smooth turn to straight front view (Human connection)
// ══════════════════════════════════════════════════════════════════════════════
const TOTAL_FRAMES = 72;
const frames = [];
let framesLoaded = 0;
const glassesCanvas = document.getElementById('glasses-3d-canvas');
const ctx = glassesCanvas ? glassesCanvas.getContext('2d', { alpha: true, desynchronized: true }) : null;

for (let i = 1; i <= TOTAL_FRAMES; i++) {
  const img = new Image();
  img.src = `website/assets/render3d/frame_${String(i).padStart(2, '0')}.png?v=34`;
  img.onload = () => {
    framesLoaded++;
    if (i === 1 && ctx) {
      renderFrame(0);
    }
  };
  frames.push(img);
}

function renderFrame(frameFloat) {
  if (!ctx || !glassesCanvas) return;
  const W = glassesCanvas.width;
  const H = glassesCanvas.height;

  // Snap to nearest frame — no crossfade needed at 72-frame density.
  // Crossfading semi-transparent PNGs (lens area has partial alpha) causes
  // alpha compounding artifacts: lens opacity oscillates mid-transition.
  // Spring physics + FRAME_LERP already provide visually smooth motion.
  const idx = clamp(Math.round(frameFloat), 0, TOTAL_FRAMES - 1);

  ctx.clearRect(0, 0, W, H);
  if (frames[idx] && frames[idx].complete) {
    ctx.globalAlpha = 1.0;
    ctx.drawImage(frames[idx], 0, 0, W, H);
  }
}

// ══════════════════════════════════════════════════════════════════════════════
//  MAIN RENDER LOOP: 4-PHASE MULTI-ANGLE BREAKDOWN & REASSEMBLY (3/4 PERSPECTIVE -> STRAIGHT)
// ══════════════════════════════════════════════════════════════════════════════
function render(p) {
  if (!storyStage) return;

  // Active step indicator across the 4 original narrative cards
  // 0: Familiar by design (0% - 22% scroll: assembled 3/4 perspective)
  // 1: Intelligence within (22% - 52% scroll: exploded components breakdown)
  // 2: Technology recedes (52% - 75% scroll: flush docking & reassembly)
  // 3: Human connection (75% - 100% scroll: graceful rotation to straight front view)
  const si = p < 0.22 ? 0 : p < 0.52 ? 1 : p < 0.75 ? 2 : 3;
  setStep(si);

  // Map progress p in [0, 1] across the 36 3D rendered frames
  const frameFloat = clamp(p * (TOTAL_FRAMES - 1), 0, TOTAL_FRAMES - 1);
  renderFrame(frameFloat);

  // Global 3D Canvas & Corner Light Cursor Parallax Tilt
  const tiltTarget = canvasWrap || glassesCanvas;
  if (tiltTarget) {
    const tiltX = (mouseY - 0.5) * -5.0;
    const tiltY = (mouseX - 0.5) * 6.0;
    tiltTarget.style.transform = `rotateX(${tiltX.toFixed(2)}deg) rotateY(${tiltY.toFixed(2)}deg)`;
  }

  // Corner Camera Indicator Light:
  // Appears from top corner of right frame (p >= 0.65).
  // Green when on light background (p ~ 0.65 - 0.74).
  // When background turns green (state-3, p >= 0.75), light turns RED!
  if (cornerLight) {
    const fIdx = clamp(frameFloat + 1, 1, TOTAL_FRAMES);
    const idx0 = Math.floor(fIdx);
    const idx1 = Math.min(TOTAL_FRAMES, idx0 + 1);
    const fract = fIdx - idx0;
    const leftPct = CORNER_COORDS[idx0][0] + (CORNER_COORDS[idx1][0] - CORNER_COORDS[idx0][0]) * fract;
    const topPct  = CORNER_COORDS[idx0][1] + (CORNER_COORDS[idx1][1] - CORNER_COORDS[idx0][1]) * fract;

    cornerLight.style.left = `${leftPct.toFixed(2)}%`;
    cornerLight.style.top  = `${topPct.toFixed(2)}%`;

    const isGreen = p >= 0.65 && p < 0.75;
    const isRed   = p >= 0.75;

    cornerLight.classList.toggle('is-green', isGreen);
    cornerLight.classList.toggle('is-red', isRed);
  }

  // Snap completion glow when turned straight and completely joined (p >= 0.88)
  if (straightGlow) {
    straightGlow.style.opacity = p >= 0.88 ? '1' : '0';
  }
}

// ── Physics Frame Loop (Motion AI Kit Spring Model) ───────────────────────────
function frame(now) {
  if (!storyLayout) return;
  const r = storyLayout.getBoundingClientRect();
  const isMobile = window.innerWidth <= 800;
  if (isMobile) {
    const stageH = storyStage ? storyStage.offsetHeight : 220;
    const stickyTop = (header ? header.offsetHeight : 68) + (quickNav ? quickNav.offsetHeight : 42) + 6;
    const d = r.height - stageH - 40;
    if (d > 0) {
      tgtP = clamp((-r.top + stickyTop) / d, 0, 1);
    }
  } else {
    const d = r.height - window.innerHeight;
    if (d > 0) tgtP = clamp(-r.top / d, 0, 1);
  }

  // Discrete time integration (clamped to prevent spiral on tab switch)
  const dt = Math.min(Math.max((now - lastFrameTime) / 1000, 0.001), 0.064);
  lastFrameTime = now;

  // Spring physics simulation: stiffness 90, damping 25, mass 1.0
  const springForce = -SPRING.stiffness * (springPos - tgtP);
  const dampingForce = -SPRING.damping * springVel;
  const accel = (springForce + dampingForce) / SPRING.mass;

  springVel += accel * dt;
  springPos += springVel * dt;

  if (Math.abs(tgtP - springPos) < SPRING.restDelta && Math.abs(springVel) < SPRING.restSpeed) {
    springPos = tgtP;
    springVel = 0;
  }
  curP = clamp(springPos, 0, 1);

  // Mouse tilt parallax
  const targetTiltX = (mouseY - 0.5) * -4.0;
  const targetTiltY = (mouseX - 0.5) * 5.0;
  curTiltX += (targetTiltX - curTiltX) * 0.08;
  curTiltY += (targetTiltY - curTiltY) * 0.08;

  render(curP);

  if (Math.abs(tgtP - curP) > 0.00005 || Math.abs(springVel) > 0.00005 || Math.abs(targetTiltX - curTiltX) > 0.01) {
    requestAnimationFrame(frame);
  } else {
    ticking = false;
  }
}

function tick() {
  chrome();
  if (!ticking) {
    ticking = true;
    lastFrameTime = performance.now();
    requestAnimationFrame(frame);
  }
}

// ── Mouse Interactivity for 3D Parallax ───────────────────────────────────────
window.addEventListener('mousemove', e => {
  mouseX = e.clientX / window.innerWidth;
  mouseY = e.clientY / window.innerHeight;
  if (!ticking) {
    ticking = true;
    lastFrameTime = performance.now();
    requestAnimationFrame(frame);
  }
}, { passive: true });

// ── Initialization ────────────────────────────────────────────────────────────
const yearEl = document.querySelector('[data-year]');
if (yearEl) yearEl.textContent = new Date().getFullYear();

window.addEventListener('scroll', tick, { passive: true });
window.addEventListener('resize', () => { chrome(); tick(); });

chrome();
render(0);

