const form = document.querySelector('#feasibility-form');
const results = document.querySelector('#results');
const errorMessage = document.querySelector('#error-message');
const submitButton = document.querySelector('#submit-button');
const saveProjectButton = document.querySelector('#save-project');
let currentPlot;
let currentReport;

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
  errorMessage.hidden = true;
  submitButton.disabled = true;
  submitButton.textContent = 'Analyzing your project…';

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
    if (!response.ok) throw new Error(body.detail?.[0]?.msg || 'Please check your entries and try again.');

    document.querySelector('#units').textContent = body.estimated_units;
    document.querySelector('#roi').textContent = `${body.estimated_roi_percentage}%`;
    document.querySelector('#revenue').textContent = formatNaira(body.projected_gross_revenue_ngn);
    document.querySelector('#coverage').textContent = `${body.max_allowable_coverage_sqm.toLocaleString()} sqm`;
    document.querySelector('#marketing-copy').textContent = body.marketing_copy_global;
    document.querySelector('#notes').innerHTML = body.fcda_compliance_notes.map((note) => `<li>${note}</li>`).join('');
    renderTrustPanel(body);
    currentPlot = { ...data, project_name: projectName };
    currentReport = body;
    saveProjectButton.hidden = false;
    results.hidden = false;
    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
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
