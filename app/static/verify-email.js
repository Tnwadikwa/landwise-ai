const form = document.querySelector('#verify-form');
const submit = document.querySelector('#verify-submit');
const message = document.querySelector('#verify-message');
const params = new URLSearchParams(window.location.search);
const emailInput = document.querySelector('#verify-email');
emailInput.value = params.get('email') || '';

window.addEventListener('load', async () => {
  const response = await fetch('/api/v1/auth/me', { credentials: 'same-origin', cache: 'no-store' });
  if (response.ok) {
    window.location.replace('/login.html');
    return;
  }
  requestAnimationFrame(() => document.body.classList.remove('is-loading'));
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const email = emailInput.value.trim();
  const code = document.querySelector('#verify-code').value.trim();
  if (!email || !/^\d{6}$/.test(code)) {
    message.className = 'message error';
    message.textContent = 'Enter the email address and six-digit code from your email.';
    message.hidden = false;
    return;
  }
  submit.disabled = true;
  try {
    const response = await fetch('/api/v1/auth/verify-email', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, code }),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail?.[0]?.msg || body.detail || 'This verification link is invalid or expired.');
    message.className = 'message success';
    message.textContent = body.message;
    message.hidden = false;
    setTimeout(() => { window.location.replace('/login.html'); }, 1600);
  } catch (error) {
    message.className = 'message error';
    message.textContent = error.message;
    message.hidden = false;
  } finally {
    submit.disabled = false;
  }
});
