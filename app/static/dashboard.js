const email = document.querySelector('#user-email');

const response = await fetch('/api/v1/auth/me');
if (!response.ok) window.location.href = '/login.html';
else email.textContent = (await response.json()).email;

document.querySelector('#logout-button').addEventListener('click', async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  button.textContent = 'Signing out…';
  try {
    await fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'same-origin' });
  } finally {
    window.location.assign('/signed-out.html');
  }
});
