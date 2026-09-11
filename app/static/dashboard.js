const email = document.querySelector('#user-email');
const projectsList = document.querySelector('#saved-projects-list');
const projectCount = document.querySelector('#project-count');
const planBadge = document.querySelector('#plan-badge');
document.querySelector('.workspace-status')?.remove();
document.querySelectorAll('.plan-badge').forEach((badge) => badge.remove());
document.querySelector('.workspace-tabs a[href="#premium"]').textContent = 'Landwise AI Plus';
document.querySelector('#premium .eyebrow').textContent = '04 · Landwise AI Plus';
document.querySelectorAll('.premium-card button').forEach((button) => {
  button.textContent = 'Available on Landwise AI Plus';
});
const workspaceTabs = [...document.querySelectorAll('.workspace-tabs a')];
const workspacePanels = [...document.querySelectorAll('.workspace-panel')];
const workspaceLinks = [...document.querySelectorAll('a[href^="#"]')];
const inactivityLimit = 60 * 60 * 1000;
let inactivityTimer;

const signOutForInactivity = async () => {
  await fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'same-origin' });
  window.location.assign('/login.html?reason=inactive');
};

const resetInactivityTimer = () => {
  window.clearTimeout(inactivityTimer);
  inactivityTimer = window.setTimeout(signOutForInactivity, inactivityLimit);
};

['click', 'keydown', 'pointermove', 'touchstart', 'scroll'].forEach((eventName) => {
  window.addEventListener(eventName, resetInactivityTimer, { passive: true });
});
resetInactivityTimer();

const showMessage = (element, text, success = false) => {
  element.textContent = text;
  element.className = `message ${success ? 'success' : 'error'}`;
  element.hidden = false;
};

const showWorkspaceSection = (sectionId) => {
  const validIds = ['home', ...workspacePanels.map((panel) => panel.id)];
  const targetId = validIds.includes(sectionId) ? sectionId : 'home';
  document.querySelector('#home').classList.toggle('is-hidden', targetId !== 'home');
  workspacePanels.forEach((panel) => {
    panel.classList.toggle('is-hidden', panel.id !== targetId);
  });
  workspaceTabs.forEach((tab) => {
    tab.classList.toggle('active', tab.getAttribute('href') === `#${targetId}`);
  });
};

workspaceLinks.forEach((link) => {
  link.addEventListener('click', (event) => {
    const targetId = link.getAttribute('href').slice(1);
    if (!document.getElementById(targetId)) return;
    event.preventDefault();
    window.history.replaceState(null, '', `#${targetId}`);
    showWorkspaceSection(targetId);
  });
});

window.addEventListener('hashchange', () => showWorkspaceSection(window.location.hash.slice(1)));
showWorkspaceSection(window.location.hash.slice(1) || 'home');

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
    meta.textContent = `${project.district} · ${project.asset_type} · ${project.stage}`;
    details.append(name, meta);
    const actions = document.createElement('div');
    actions.className = 'saved-project-actions';
    const compare = document.createElement('input');
    compare.type = 'checkbox';
    compare.className = 'compare-project';
    compare.value = project.id;
    compare.setAttribute('aria-label', `Compare ${project.name}`);
    compare.addEventListener('change', () => renderComparison(projects));
    const download = document.createElement('a');
    download.className = 'text-button';
    download.href = `/api/v1/projects/${project.id}/report.pdf`;
    download.textContent = 'Download PDF';
    const upload = document.createElement('button');
    upload.className = 'text-button';
    upload.textContent = 'Upload document';
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.pdf,image/jpeg,image/png';
    fileInput.hidden = true;
    upload.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', async () => {
      const [file] = fileInput.files;
      if (!file) return;
      upload.disabled = true;
      upload.textContent = 'Uploading...';
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch(`/api/v1/projects/${project.id}/documents`, { method: 'POST', body: formData });
      if (response.ok) loadProjects();
      else {
        const body = await response.json();
        upload.textContent = body.detail || 'Upload failed';
        upload.disabled = false;
      }
    });
    const viewDocuments = document.createElement('button');
    viewDocuments.className = 'text-button';
    viewDocuments.textContent = `View documents (${project.document_count})`;
    viewDocuments.disabled = project.document_count === 0;
    viewDocuments.addEventListener('click', async () => {
      viewDocuments.disabled = true;
      viewDocuments.textContent = 'Loading documents...';
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 10000);
      let response;
      try {
        response = await fetch(`/api/v1/projects/${project.id}/documents`, { signal: controller.signal });
      } catch {
        viewDocuments.textContent = 'Document list timed out';
        viewDocuments.disabled = false;
        return;
      } finally {
        window.clearTimeout(timeout);
      }
      if (!response.ok) {
        viewDocuments.textContent = 'Could not load documents';
        viewDocuments.disabled = false;
        return;
      }
      const documents = await response.json();
      const existingList = card.querySelector('.document-list');
      if (existingList) {
        existingList.remove();
        viewDocuments.disabled = false;
        viewDocuments.textContent = `View documents (${project.document_count})`;
        return;
      }
      if (!documents.length) {
        viewDocuments.textContent = 'No documents uploaded';
        viewDocuments.disabled = false;
        return;
      }
      const documentList = document.createElement('div');
      documentList.className = 'document-list';
      documents.forEach((document) => {
        const row = document.createElement('div');
        row.className = 'document-row';
        const name = document.createElement('span');
        name.textContent = document.name;
        const actions = document.createElement('div');
        const open = document.createElement('a');
        open.className = 'text-button';
        open.href = `/api/v1/projects/${project.id}/documents/${document.id}`;
        open.target = '_blank';
        open.rel = 'noreferrer';
        open.textContent = 'Open';
        const pdf = document.createElement('a');
        pdf.className = 'pdf-document-button';
        pdf.href = `/api/v1/projects/${project.id}/documents/${document.id}/pdf`;
        pdf.target = '_blank';
        pdf.rel = 'noreferrer';
        pdf.textContent = 'PDF';
        pdf.title = 'Open as PDF';
        pdf.setAttribute('aria-label', `Open ${document.name} as PDF`);
        actions.append(open, pdf);
        row.append(name, actions);
        documentList.append(row);
      });
      card.append(documentList);
      viewDocuments.disabled = false;
      viewDocuments.textContent = `Hide documents (${documents.length})`;
    });
    const review = document.createElement('button');
    review.className = 'text-button';
    review.textContent = project.review_status ? 'Review requested' : 'Request review';
    review.disabled = Boolean(project.review_status);
    review.addEventListener('click', async () => {
      const note = window.prompt('What should the professional review?');
      if (note === null) return;
      review.disabled = true;
      const response = await fetch(`/api/v1/projects/${project.id}/professional-review`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ note }),
      });
      if (response.ok) loadProjects();
      else review.disabled = false;
    });
    const remove = document.createElement('button');
    remove.className = 'text-button';
    remove.textContent = 'Delete';
    remove.addEventListener('click', async () => {
      remove.disabled = true;
      const response = await fetch(`/api/v1/projects/${project.id}`, { method: 'DELETE' });
      if (response.ok) loadProjects();
      else remove.disabled = false;
    });
    actions.append(compare, fileInput, upload, viewDocuments, review, download, remove);
    card.append(details, actions);
    projectsList.append(card);
  });
};

const renderComparison = (projects) => {
  const selectedIds = [...document.querySelectorAll('.compare-project:checked')].map((input) => input.value);
  const selected = projects.filter((project) => selectedIds.includes(project.id));
  const panel = document.querySelector('#comparison-panel');
  const results = document.querySelector('#comparison-results');
  panel.hidden = selected.length < 2;
  results.replaceChildren();
  selected.slice(0, 3).forEach((project) => {
    const item = document.createElement('article');
    item.className = 'comparison-item';
    item.innerHTML = `<strong>${project.name}</strong><span>${project.asset_type}</span><b>${project.estimated_roi_percentage}% ROI</b><small>${formatNaira(project.projected_gross_revenue_ngn)} revenue</small>`;
    results.append(item);
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
