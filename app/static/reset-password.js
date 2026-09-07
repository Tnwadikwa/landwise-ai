const form = document.querySelector('#reset-form');
const submit = document.querySelector('#reset-submit');
const message = document.querySelector('#reset-message');
const password = document.querySelector('[name="password"]');
const toggle = document.querySelector('#toggle-reset-password');
const token = new URLSearchParams(window.location.search).get('token');

toggle.addEventListener('click', () => {
  const isHidden = password.type === 'password';
  password.type = isHidden ? 'text' : 'password';
  toggle.textContent = isHidden ? 'Hide' : 'Show';
  toggle.setAttribute('aria-label', `${isHidden ? 'Hide' : 'Show'} password`);
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!token) { message.className = 'message error'; message.textContent = 'This reset link is missing or invalid.'; message.hidden = false; return; }
  submit.disabled = true;
  try {
    const response = await fetch('/api/v1/auth/reset-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token, password: password.value }) });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail?.[0]?.msg || body.detail || 'This reset link is invalid or expired.');
    message.className = 'message success';
    message.textContent = body.message;
    message.hidden = false;
    form.reset();
    setTimeout(() => { window.location.href = '/login.html'; }, 1600);
  } catch (error) { message.className = 'message error'; message.textContent = error.message; message.hidden = false; }
  finally { submit.disabled = false; }
});
