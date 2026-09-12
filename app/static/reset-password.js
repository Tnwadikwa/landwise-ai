const form = document.querySelector('#reset-form');
const submit = document.querySelector('#reset-submit');
const message = document.querySelector('#reset-message');
const password = document.querySelector('[name="password"]');
const confirmPassword = document.querySelector('[name="confirm_password"]');
const toggle = document.querySelector('#toggle-reset-password');
const confirmToggle = document.querySelector('#toggle-confirm-reset-password');
const token = new URLSearchParams(window.location.search).get('token');

const updatePasswordMatch = () => {
  const labels = [password.closest('label'), confirmPassword.closest('label')];
  labels.forEach((label) => label.classList.remove('password-match', 'password-mismatch'));
  if (!confirmPassword.value) return;
  labels.forEach((label) => label.classList.add(password.value === confirmPassword.value ? 'password-match' : 'password-mismatch'));
};

password.addEventListener('input', updatePasswordMatch);
confirmPassword.addEventListener('input', updatePasswordMatch);

toggle.addEventListener('click', () => {
  const isHidden = password.type === 'password';
  password.type = isHidden ? 'text' : 'password';
  toggle.textContent = isHidden ? 'Hide' : 'Show';
  toggle.setAttribute('aria-label', `${isHidden ? 'Hide' : 'Show'} password`);
});

confirmToggle.addEventListener('click', () => {
  const isHidden = confirmPassword.type === 'password';
  confirmPassword.type = isHidden ? 'text' : 'password';
  confirmToggle.textContent = isHidden ? 'Hide' : 'Show';
  confirmToggle.setAttribute('aria-label', `${isHidden ? 'Hide' : 'Show'} confirm password`);
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!token) { message.className = 'message error'; message.textContent = 'This reset link is missing or invalid.'; message.hidden = false; return; }
  if (password.value !== confirmPassword.value) { updatePasswordMatch(); message.className = 'message error'; message.textContent = 'Passwords do not match.'; message.hidden = false; return; }
  submit.disabled = true;
  try {
    const response = await fetch('/api/v1/auth/reset-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token, password: password.value, confirm_password: confirmPassword.value }) });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail?.[0]?.msg || body.detail || 'This reset link is invalid or expired.');
    message.className = 'message success';
    message.textContent = body.message;
    message.hidden = false;
    form.reset();
    setTimeout(() => { window.location.replace('/login.html'); }, 1600);
  } catch (error) { message.className = 'message error'; message.textContent = error.message; message.hidden = false; }
  finally { submit.disabled = false; }
});
