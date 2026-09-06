const form = document.querySelector('#feasibility-form');
const results = document.querySelector('#results');
const errorMessage = document.querySelector('#error-message');
const submitButton = document.querySelector('#submit-button');

const formatNaira = (value) => new Intl.NumberFormat('en-NG', {
  style: 'currency', currency: 'NGN', maximumFractionDigits: 0,
}).format(value);

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  errorMessage.hidden = true;
  submitButton.disabled = true;
  submitButton.textContent = 'Analyzing your project…';

  const data = Object.fromEntries(new FormData(form));
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
  form.reset();
  document.querySelector('#analyzer').scrollIntoView({ behavior: 'smooth' });
});

document.querySelector('#copy-marketing').addEventListener('click', async (event) => {
  await navigator.clipboard.writeText(document.querySelector('#marketing-copy').textContent);
  event.target.textContent = 'Copied ✓';
  setTimeout(() => { event.target.textContent = 'Copy marketing copy'; }, 1800);
});
