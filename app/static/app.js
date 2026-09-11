const form = document.querySelector('#feasibility-form');
const results = document.querySelector('#results');
const errorMessage = document.querySelector('#error-message');
const submitButton = document.querySelector('#submit-button');
const saveProjectButton = document.querySelector('#save-project');
let currentPlot;
let currentReport;
const progressLabel = document.querySelector('.form-progress-label');
const formHeading = document.querySelector('.form-card-heading');
const analysisProgress = document.createElement('div');
analysisProgress.className = 'analysis-progress';
analysisProgress.hidden = true;
analysisProgress.setAttribute('role', 'status');
analysisProgress.innerHTML = '<span class="progress-dot"></span><span id="analysis-progress-text">Verifying location</span><div class="progress-track"><span></span></div>';
formHeading.after(analysisProgress);

const addTooltip = (selector, text) => {
  const input = document.querySelector(selector);
  const label = input?.closest('label');
  if (!label) return;
  const button = document.createElement('button');
  button.className = 'term-tooltip';
  button.type = 'button';
  button.textContent = '?';
  button.setAttribute('aria-label', text);
  button.dataset.tooltip = text;
  label.append(button);
};

addTooltip('[name="title_type"]', 'Title type is the legal basis for holding or using the land, such as a Certificate of Occupancy or Right of Occupancy.');
addTooltip('[name="cadastral_zone"]', 'A cadastral zone is an official land-administration area used to identify plots and planning records.');

const addMetricTooltip = (id, text) => {
  const metric = document.querySelector(id).closest('article');
  const label = metric.querySelector('span');
  const button = document.createElement('button');
  button.className = 'term-tooltip';
  button.type = 'button';
  button.textContent = '?';
  button.setAttribute('aria-label', text);
  button.dataset.tooltip = text;
  label.append(button);
};

addMetricTooltip('#roi', 'ROI means return on investment: the estimated gain or loss compared with the total acquisition and construction cost.');
addMetricTooltip('#coverage', 'Buildable coverage is the estimated maximum land area that the building may cover at ground level, subject to formal planning approval.');

const progressSteps = ['Verifying location', 'Checking land details', 'Building estimate'];
const startAnalysisProgress = () => {
  let step = 0;
  analysisProgress.hidden = false;
  progressLabel.textContent = progressSteps[step];
  document.querySelector('#analysis-progress-text').textContent = progressSteps[step];
  return window.setInterval(() => {
    step = Math.min(step + 1, progressSteps.length - 1);
    progressLabel.textContent = progressSteps[step];
    document.querySelector('#analysis-progress-text').textContent = progressSteps[step];
  }, 1100);
};

const stopAnalysisProgress = () => {
  analysisProgress.hidden = true;
  progressLabel.textContent = 'Ready to analyze';
};

const fieldLabels = [...form.querySelectorAll('.form-grid label')];
const clearFieldStates = () => fieldLabels.forEach((label) => {
  label.classList.remove('is-valid', 'is-invalid');
});
const setFieldState = (fieldName, state) => {
  const input = form.elements.namedItem(fieldName);
  const label = input?.closest('label');
  if (label) label.classList.add(state);
};
const matchingField = (message) => {
  const value = message.toLowerCase();
  if (value.includes('district') || value.includes('locality') || value.includes('location')) return 'district';
  if (value.includes('title type') || value.includes('title')) return 'title_type';
  if (value.includes('cadastral')) return 'cadastral_zone';
  if (value.includes('plot size') || value.includes('measurement')) return 'plot_size_sqm';
  if (value.includes('acquisition') || value.includes('amount')) return 'acquisition_cost_ngn';
  if (value.includes('asset') || value.includes('development')) return 'target_asset_type';
  return undefined;
};

form.addEventListener('invalid', (event) => {
  event.target.closest('label')?.classList.add('is-invalid');
}, true);

form.addEventListener('input', (event) => {
  const label = event.target.closest('label');
  label?.classList.remove('is-invalid', 'is-valid');
});

const formatNaira = (value) => new Intl.NumberFormat('en-NG', {
  style: 'currency', currency: 'NGN', maximumFractionDigits: 0,
}).format(value);

const getTrustPanel = () => {
  let panel = document.querySelector('#trust-panel');
  if (panel) return panel;
  panel = document.createElement('section');
  panel.id = 'trust-panel';
  panel.className = 'trust-panel';
  panel.innerHTML = '<div class="trust-panel-heading"><div><p class="eyebrow">Verification and sources</p><h3>Know what supports this estimate</h3></div><strong id="confidence-level" class="confidence-badge"></strong></div><a id="verified-location-map" class="verified-location-map" target="_blank" rel="noreferrer" hidden></a><div class="trust-grid"><section><h4>Verification status</h4><ul id="verification-checks" class="verification-checks"></ul></section><section><h4>Assumptions used</h4><ul id="assumptions-list" class="assumptions-list"></ul></section></div>';
  document.querySelector('#results .next-step').before(panel);
  return panel;
};

const renderTrustPanel = (body) => {
  const panel = getTrustPanel();
  const location = body.verified_location;
  document.querySelector('#confidence-level').textContent = `${body.confidence_level} confidence`;
  document.querySelector('#verification-checks').replaceChildren(...body.verification_checks.map((check) => {
    const item = document.createElement('li');
    item.className = `verification-${check.status}`;
    item.textContent = `${check.label}: ${check.detail}`;
    return item;
  }));
  document.querySelector('#assumptions-list').replaceChildren(...body.assumptions.map((assumption) => {
    const item = document.createElement('li');
    item.textContent = assumption;
    return item;
  }));
  const map = document.querySelector('#verified-location-map');
  map.hidden = !location;
  if (location) {
    map.href = `https://www.openstreetmap.org/search?query=${encodeURIComponent(location)}`;
    map.textContent = `Confirm location: ${location}`;
  }
  panel.hidden = false;
};

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  clearFieldStates();
  errorMessage.hidden = true;
  submitButton.disabled = true;
  submitButton.textContent = 'Analyzing your project…';
  const progressTimer = startAnalysisProgress();

  const data = Object.fromEntries(new FormData(form));
  const projectName = data.project_name;
  delete data.project_name;
  data.plot_size_sqm = Number(data.plot_size_sqm);
  data.acquisition_cost_ngn = Number(data.acquisition_cost_ngn);

  try {
    const response = await fetch('/api/v1/feasibility/generate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : body.detail?.[0]?.msg || 'Please check your entries and try again.');

    document.querySelector('#units').textContent = body.estimated_units;
    document.querySelector('#roi').textContent = `${body.estimated_roi_percentage}%`;
    document.querySelector('#revenue').textContent = formatNaira(body.projected_gross_revenue_ngn);
    document.querySelector('#coverage').textContent = `${body.max_allowable_coverage_sqm.toLocaleString()} sqm`;
    document.querySelector('#marketing-copy').textContent = body.marketing_copy_global;
    document.querySelector('#notes').innerHTML = body.fcda_compliance_notes.map((note) => `<li>${note}</li>`).join('');
    renderTrustPanel(body);
    currentPlot = { ...data, project_name: projectName };
    currentReport = body;
    fieldLabels.forEach((label) => label.classList.add('is-valid'));
    saveProjectButton.hidden = false;
    results.hidden = false;
    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    const fieldName = matchingField(error.message);
    if (fieldName) setFieldState(fieldName, 'is-invalid');
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    window.clearInterval(progressTimer);
    stopAnalysisProgress();
    submitButton.disabled = false;
    submitButton.innerHTML = 'Generate my feasibility plan <span>→</span>';
  }
});

document.querySelector('#new-analysis').addEventListener('click', () => {
  results.hidden = true;
  saveProjectButton.hidden = true;
  currentPlot = undefined;
  currentReport = undefined;
  document.querySelector('#trust-panel')?.setAttribute('hidden', '');
  form.reset();
  document.querySelector('#analyzer').scrollIntoView({ behavior: 'smooth' });
});

saveProjectButton.addEventListener('click', async () => {
  saveProjectButton.disabled = true;
  saveProjectButton.textContent = 'Saving…';
  try {
    const response = await fetch('/api/v1/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: currentPlot.project_name, plot: currentPlot, report: currentReport }),
    });
    if (!response.ok) throw new Error('Your project could not be saved.');
    saveProjectButton.textContent = 'Saved';
    window.dispatchEvent(new Event('projects-updated'));
  } catch (error) {
    saveProjectButton.textContent = error.message;
  } finally {
    setTimeout(() => { saveProjectButton.disabled = false; saveProjectButton.textContent = 'Save project'; }, 1800);
  }
});

document.querySelector('#copy-marketing').addEventListener('click', async (event) => {
  await navigator.clipboard.writeText(document.querySelector('#marketing-copy').textContent);
  event.target.textContent = 'Copied ✓';
  setTimeout(() => { event.target.textContent = 'Copy marketing copy'; }, 1800);
});
