const email = document.querySelector('#user-email');
const projectsList = document.querySelector('#saved-projects-list');
const projectCount = document.querySelector('#project-count');

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

  email.textContent = (await response.json()).email;
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
