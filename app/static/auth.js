document.body.classList.remove('is-loading');

document.body.classList.remove('is-loading');

const navigateWithTransition = (url) => {
  document.body.classList.add('is-transitioning');
  setTimeout(() => { window.location.href = url; }, 150);
};

const form = document.querySelector('#auth-form');
form.noValidate = true;
const message = document.querySelector('#auth-message');
const resendVerification = document.querySelector('#resend-verification');
const submit = document.querySelector('#auth-submit');
const passwordInput = document.querySelector('[name="password"]');
const togglePassword = document.querySelector('#toggle-password');
let mode = 'login';
const recoveryLink = document.querySelector('.recovery-link');
const profileFields = document.createElement('div');
profileFields.id = 'profile-fields';
profileFields.innerHTML = '<label>First name<input name="first_name" autocomplete="given-name" /></label><label>Surname<input name="surname" autocomplete="family-name" /></label><label>Date of birth<input name="date_of_birth" type="date" autocomplete="bday" /></label><label>Gender<select name="gender"><option value="" selected disabled>Select an option</option><option>Woman</option><option>Man</option><option>Non-binary</option><option>Prefer not to say</option></select></label>';
const confirmPasswordField = document.createElement('div');
confirmPasswordField.id = 'confirm-password-field';
confirmPasswordField.innerHTML = '<label id="confirm-password-label">Confirm password<div class="password-field"><input name="confirm_password" type="password" autocomplete="new-password" /><button type="button" id="toggle-confirm-password" aria-label="Show confirm password">Show</button></div></label>';

const setRegisterFields = (visible) => {
  profileFields.hidden = !visible;
  profileFields.querySelectorAll('input, select').forEach((input) => { input.required = visible; });
  confirmPasswordField.hidden = !visible;
  confirmPasswordField.querySelector('input').required = visible;
  recoveryLink.hidden = visible;
  if (visible && !profileFields.isConnected) form.querySelector('[name="email"]').closest('label').before(profileFields);
  if (visible && !confirmPasswordField.isConnected) passwordInput.closest('label').after(confirmPasswordField);
};

const updatePasswordMatch = () => {
  const confirmPassword = confirmPasswordField.querySelector('[name="confirm_password"]');
  const labels = [passwordInput.closest('label'), confirmPassword.closest('label')];
  labels.forEach((label) => label.classList.remove('password-match', 'password-mismatch'));
  if (!confirmPassword.value) return;
  labels.forEach((label) => label.classList.add(passwordInput.value === confirmPassword.value ? 'password-match' : 'password-mismatch'));
};

const clearRegistrationFieldStates = () => {
  form.querySelectorAll('label').forEach((label) => label.classList.remove('field-invalid'));
};

const highlightInvalidRegistrationFields = () => {
  let hasInvalidField = false;
  form.querySelectorAll('input[required], select[required]').forEach((field) => {
    const invalid = !field.checkValidity();
    field.closest('label')?.classList.toggle('field-invalid', invalid);
    hasInvalidField ||= invalid;
  });
  return hasInvalidField;
};

passwordInput.addEventListener('input', updatePasswordMatch);
confirmPasswordField.addEventListener('input', updatePasswordMatch);
form.addEventListener('input', (event) => event.target.closest('label')?.classList.remove('field-invalid'));
form.addEventListener('change', (event) => event.target.closest('label')?.classList.remove('field-invalid'));

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

resendVerification.addEventListener('click', async () => {
  resendVerification.disabled = true;
  try {
    const response = await fetch('/api/v1/auth/resend-verification', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: form.querySelector('[name="email"]').value }),
    });
    const body = await response.json();
    showMessage(body.detail || body.message || 'We could not resend the verification email.', !response.ok);
  } finally {
    resendVerification.disabled = false;
  }
});

const setMode = (nextMode) => {
  mode = nextMode;
  document.querySelectorAll('[data-mode]').forEach((item) => item.classList.toggle('active', item.dataset.mode === mode));
  submit.innerHTML = mode === 'login' ? 'Sign in <span>→</span>' : 'Create account <span>→</span>';
  form.querySelector('[name=password]').autocomplete = mode === 'login' ? 'current-password' : 'new-password';
  setRegisterFields(mode === 'register');
  message.hidden = true;
  resendVerification.hidden = true;
};

document.querySelectorAll('[data-mode]').forEach((tab) => tab.addEventListener('click', () => setMode(tab.dataset.mode)));

if (new URLSearchParams(window.location.search).get('mode') === 'register') setMode('register');

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (mode === 'register' && highlightInvalidRegistrationFields()) {
    showMessage('Complete all required fields before creating an account.', true);
    return;
  }
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
      if (body.verification_required === 'true') {
        window.location.href = `/verify-email.html?email=${encodeURIComponent(payload.email)}`;
      } else {
        navigateWithTransition('/dashboard.html');
      }
    } else {
      navigateWithTransition('/dashboard.html');
    }
  } catch (error) {
    showMessage(error.message, true);
    resendVerification.hidden = !(mode === 'login' && error.message.toLowerCase().includes('verify your email'));
  }
  finally { submit.disabled = false; }
});

document.addEventListener('click', (event) => {
  if (event.target.id !== 'toggle-confirm-password') return;
  const input = confirmPasswordField.querySelector('[name="confirm_password"]');
  const hidden = input.type === 'password';
  input.type = hidden ? 'text' : 'password';
  event.target.textContent = hidden ? 'Hide' : 'Show';
});
