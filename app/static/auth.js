const form = document.querySelector('#auth-form');
const message = document.querySelector('#auth-message');
const submit = document.querySelector('#auth-submit');
const passwordInput = document.querySelector('[name="password"]');
const togglePassword = document.querySelector('#toggle-password');
let mode = 'login';
const recoveryLink = document.querySelector('.recovery-link');
const profileFields = document.createElement('div');
profileFields.id = 'profile-fields';
profileFields.innerHTML = '<label>First name<input name="first_name" autocomplete="given-name" /></label><label>Surname<input name="surname" autocomplete="family-name" /></label><label>Date of birth<input name="date_of_birth" type="date" autocomplete="bday" /></label><label>Gender<select name="gender"><option value="" selected disabled>Select an option</option><option>Woman</option><option>Man</option><option>Non-binary</option><option>Prefer not to say</option></select></label><label id="confirm-password-label">Confirm password<div class="password-field"><input name="confirm_password" type="password" autocomplete="new-password" /><button type="button" id="toggle-confirm-password" aria-label="Show confirm password">Show</button></div></label>';

const setRegisterFields = (visible) => {
  profileFields.hidden = !visible;
  profileFields.querySelectorAll('input, select').forEach((input) => { input.required = visible; });
  recoveryLink.hidden = visible;
  if (visible && !profileFields.isConnected) recoveryLink.before(profileFields);
};

const updatePasswordMatch = () => {
  const confirmPassword = profileFields.querySelector('[name="confirm_password"]');
  const labels = [passwordInput.closest('label'), confirmPassword.closest('label')];
  labels.forEach((label) => label.classList.remove('password-match', 'password-mismatch'));
  if (!confirmPassword.value) return;
  labels.forEach((label) => label.classList.add(passwordInput.value === confirmPassword.value ? 'password-match' : 'password-mismatch'));
};

passwordInput.addEventListener('input', updatePasswordMatch);
profileFields.addEventListener('input', updatePasswordMatch);

togglePassword.addEventListener('click', () => {
  const isHidden = passwordInput.type === 'password';
  passwordInput.type = isHidden ? 'text' : 'password';
  togglePassword.textContent = isHidden ? 'Hide' : 'Show';
  togglePassword.setAttribute('aria-label', `${isHidden ? 'Hide' : 'Show'} password`);
});

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
  setRegisterFields(mode === 'register');
  message.hidden = true;
}));

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  submit.disabled = true;
  message.hidden = true;
  const payload = Object.fromEntries(new FormData(form));
  if (mode === 'register' && payload.password !== payload.confirm_password) {
    updatePasswordMatch();
    showMessage('Passwords do not match.', true);
    submit.disabled = false;
    return;
  }
  try {
    const response = await fetch(`/api/v1/auth/${mode}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const body = await response.json();
    if (!response.ok) {
      const detail = body.detail?.[0]?.msg || body.detail || 'Something went wrong.';
      throw new Error(detail.replace('Value error, ', '').replace('value is not a valid email address: ', 'Please enter a valid email address: '));
    }
    if (mode === 'register') {
      window.location.href = '/dashboard.html';
    } else {
      window.location.href = '/dashboard.html';
    }
  } catch (error) { showMessage(error.message, true); }
  finally { submit.disabled = false; }
});

document.addEventListener('click', (event) => {
  if (event.target.id !== 'toggle-confirm-password') return;
  const input = profileFields.querySelector('[name="confirm_password"]');
  const hidden = input.type === 'password';
  input.type = hidden ? 'text' : 'password';
  event.target.textContent = hidden ? 'Hide' : 'Show';
});
