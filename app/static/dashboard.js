const email = document.querySelector('#user-email');
const projectsList = document.querySelector('#saved-projects-list');
const projectCount = document.querySelector('#project-count');
const planBadge = document.querySelector('#plan-badge');

const showMessage = (element, text, success = false) => {
  element.textContent = text;
  element.className = `message ${success ? 'success' : 'error'}`;
  element.hidden = false;
};

const renderProjects = (projects) => {
  projectCount.textContent = projects.length;
  projectsList.replaceChildren();
  if (!projects.length) {
    const empty = document.createElement('p');
    empty.className = 'muted-small';
    empty.textContent = 'Your saved analyses will appear here.';
    projectsList.append(empty);
    return;
  }
  projects.forEach((project) => {
    const card = document.createElement('article');
    card.className = 'saved-project';
    const details = document.createElement('div');
    const name = document.createElement('strong');
    name.textContent = project.name;
    const meta = document.createElement('span');
    meta.textContent = `${project.district} · ${project.asset_type}`;
    details.append(name, meta);
    const actions = document.createElement('div');
    actions.className = 'saved-project-actions';
    const download = document.createElement('a');
    download.className = 'text-button';
    download.href = `/api/v1/projects/${project.id}/report.pdf`;
    download.textContent = 'Download PDF';
    const remove = document.createElement('button');
    remove.className = 'text-button';
    remove.textContent = 'Delete';
    remove.addEventListener('click', async () => {
      remove.disabled = true;
      const response = await fetch(`/api/v1/projects/${project.id}`, { method: 'DELETE' });
      if (response.ok) loadProjects();
      else remove.disabled = false;
    });
    actions.append(download, remove);
    card.append(details, actions);
    projectsList.append(card);
  });
};

const loadProjects = async () => {
  const response = await fetch('/api/v1/projects');
  if (response.ok) renderProjects(await response.json());
};

window.addEventListener('projects-updated', loadProjects);

(async () => {
  const response = await fetch('/api/v1/auth/me', { credentials: 'same-origin' });
  if (!response.ok) {
    window.location.href = '/login.html';
    return;
  }

  const account = await response.json();
  email.textContent = account.email;
  planBadge.textContent = account.plan === 'paid' ? 'Paid plan' : 'Free plan';
  loadProjects();
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
})().catch(() => {
  window.location.href = '/login.html';
});

document.querySelector('#change-password-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const message = document.querySelector('#password-message');
  const response = await fetch('/api/v1/auth/change-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))) });
  const body = await response.json();
  if (!response.ok) return showMessage(message, body.detail || 'Password change failed.');
  showMessage(message, body.message, true);
  setTimeout(() => { window.location.href = '/login.html'; }, 1200);
});

document.querySelector('#logout-all').addEventListener('click', async () => {
  const response = await fetch('/api/v1/auth/logout-all', { method: 'POST' });
  const body = await response.json();
  if (response.ok) window.location.href = '/login.html';
  else showMessage(document.querySelector('#account-message'), body.detail || 'Could not sign out all devices.');
});

document.querySelector('#delete-account').addEventListener('click', async () => {
  const password = window.prompt('Enter your password to permanently delete your account and saved projects.');
  if (!password) return;
  const response = await fetch('/api/v1/auth/account', { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password }) });
  const body = await response.json();
  if (response.ok) window.location.href = '/signed-out.html';
  else showMessage(document.querySelector('#account-message'), body.detail || 'Account deletion failed.');
});
