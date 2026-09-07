const email = document.querySelector('#user-email');

const response = await fetch('/api/v1/auth/me');
if (!response.ok) window.location.href = '/login.html';
else email.textContent = (await response.json()).email;

document.querySelector('#logout-button').addEventListener('click', async () => {
  await fetch('/api/v1/auth/logout', { method: 'POST' });
  window.location.href = '/';
});
