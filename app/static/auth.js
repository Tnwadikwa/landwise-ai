const form = document.querySelector('#auth-form');
const message = document.querySelector('#auth-message');
const submit = document.querySelector('#auth-submit');
let mode = 'login';

const showMessage = (text, isError = false) => {
  message.textContent = text;
  message.className = `message ${isError ? 'error' : 'success'}`;
  message.hidden = false;
};

document.querySelectorAll('[data-mode]').forEach((tab) => tab.addEventListener('click', () => {
  mode = tab.dataset.mode;
  document.querySelectorAll('[data-mode]').forEach((item) => item.classList.toggle('active', item === tab));
  submit.innerHTML = mode === 'login' ? 'Sign in <span>→</span>' : 'Create account <span>→</span>';
  form.querySelector('[name=password]').autocomplete = mode === 'login' ? 'current-password' : 'new-password';
  message.hidden = true;
}));

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  submit.disabled = true;
  message.hidden = true;
  const payload = Object.fromEntries(new FormData(form));
  try {
    const response = await fetch(`/api/v1/auth/${mode}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const body = await response.json();
    if (!response.ok) {
      const detail = body.detail?.[0]?.msg || body.detail || 'Something went wrong.';
      throw new Error(detail.replace('Value error, ', '').replace('value is not a valid email address: ', 'Please enter a valid email address: '));
    }
    if (mode === 'register') {
      mode = 'login';
      document.querySelector('[data-mode="login"]').click();
      showMessage('Account created. You can now sign in.');
    } else {
      window.location.href = '/dashboard.html';
    }
  } catch (error) { showMessage(error.message, true); }
  finally { submit.disabled = false; }
});
