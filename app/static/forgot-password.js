const form = document.querySelector('#forgot-form');
const submit = document.querySelector('#forgot-submit');
const message = document.querySelector('#forgot-message');

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  submit.disabled = true;
  submit.textContent = 'Sending…';
  try {
    const response = await fetch('/api/v1/auth/forgot-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(Object.fromEntries(new FormData(form))) });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail?.[0]?.msg || body.detail || 'Please check your email address.');
    message.className = 'message success';
    message.textContent = body.message;
    message.hidden = false;
    form.reset();
  } catch (error) {
    message.className = 'message error';
    message.textContent = error.message;
    message.hidden = false;
  } finally {
    submit.disabled = false;
    submit.innerHTML = 'Send email <span>→</span>';
  }
});
