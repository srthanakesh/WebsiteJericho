const header = document.querySelector('[data-header]');
const menuButton = document.querySelector('[data-menu-button]');
const nav = document.querySelector('[data-nav]');
const progress = document.querySelector('.scroll-progress span');
const storyStage = document.querySelector('[data-story-stage]');
const storySteps = [...document.querySelectorAll('[data-story-step]')];
const stageNumber = document.querySelector('[data-stage-number]');
const stageLabel = document.querySelector('[data-stage-label]');
const stageProgress = document.querySelector('[data-stage-progress]');

function updatePageChrome() {
  const y = window.scrollY;
  header?.classList.toggle('is-scrolled', y > 24);

  const max = document.documentElement.scrollHeight - window.innerHeight;
  const ratio = max > 0 ? Math.min(1, y / max) : 0;
  if (progress) progress.style.transform = `scaleX(${ratio})`;
}

menuButton?.addEventListener('click', () => {
  const open = menuButton.getAttribute('aria-expanded') === 'true';
  menuButton.setAttribute('aria-expanded', String(!open));
  nav?.classList.toggle('is-open', !open);
  document.body.classList.toggle('menu-open', !open);
});

nav?.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', () => {
    menuButton?.setAttribute('aria-expanded', 'false');
    nav.classList.remove('is-open');
    document.body.classList.remove('menu-open');
  });
});

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('is-visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });

document.querySelectorAll('.reveal').forEach((item) => revealObserver.observe(item));

function setStoryState(index) {
  if (!storyStage) return;
  storyStage.classList.remove('state-0', 'state-1', 'state-2', 'state-3');
  storyStage.classList.add(`state-${index}`);
  storySteps.forEach((step) => step.classList.toggle('is-active', Number(step.dataset.storyStep) === index));

  const active = storySteps.find((step) => Number(step.dataset.storyStep) === index);
  if (stageNumber) stageNumber.textContent = String(index + 1).padStart(2, '0');
  if (stageLabel && active) stageLabel.textContent = active.dataset.label || '';
  if (stageProgress) stageProgress.style.width = `${((index + 1) / storySteps.length) * 100}%`;
}

const storyObserver = new IntersectionObserver((entries) => {
  const visible = entries
    .filter((entry) => entry.isIntersecting)
    .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];

  if (visible) setStoryState(Number(visible.target.dataset.storyStep));
}, { threshold: [0.25, 0.45, 0.65], rootMargin: '-18% 0px -30% 0px' });

storySteps.forEach((step) => storyObserver.observe(step));

document.querySelector('[data-year]').textContent = new Date().getFullYear();
window.addEventListener('scroll', updatePageChrome, { passive: true });
window.addEventListener('resize', updatePageChrome);
updatePageChrome();
setStoryState(0);
