(() => {
  'use strict';
  const root = document.getElementById('converter');
  const find = id => document.getElementById(id);
  const input = find('file-input');
  const list = find('file-list');
  const convertButton = find('convert-button');
  const errorMessage = find('error-message');
  const storageKey = 'suite.wordToPdf.job';
  let files = [];
  let jobId = null;
  let locked = false;
  let available = true;
  let pollGeneration = 0;
  let expiryTimer = null;
  const maxFiles = Number(root.dataset.maxFiles);
  const maxFileBytes = Number(root.dataset.maxFileBytes);
  const maxTotalBytes = Number(root.dataset.maxTotalBytes);
  const formatSize = bytes => {
    const unit = bytes < 1024 ? 'B' : bytes < 1024 * 1024 ? 'KB' : 'MB';
    const divisor = unit === 'B' ? 1 : unit === 'KB' ? 1024 : 1024 * 1024;
    return `${(bytes / divisor).toLocaleString('pt-BR', { maximumFractionDigits: 2 })} ${unit}`;
  };
  const remember = value => { try { value ? sessionStorage.setItem(storageKey, value) : sessionStorage.removeItem(storageKey); } catch {} };
  const showError = message => { errorMessage.textContent = message; errorMessage.hidden = !message; };

  async function request(url, options) {
    const response = await fetch(url, { cache: 'no-store', ...options });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      const error = new Error(typeof payload.detail === 'string' ? payload.detail : 'Não foi possível concluir a solicitação.');
      error.status = response.status;
      throw error;
    }
    return response.status === 204 ? null : response.json();
  }

  function setLocked(value) {
    locked = value;
    find('file-controls').disabled = value;
    convertButton.disabled = value || !available || !files.length;
  }

  function renderSelection() {
    list.replaceChildren();
    files.forEach((file, index) => {
      const item = document.createElement('li');
      const description = document.createElement('span');
      description.className = 'file-description';
      const name = document.createElement('span');
      name.textContent = file.name;
      const size = document.createElement('small');
      size.textContent = formatSize(file.size);
      description.append(name, size);
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'text-button';
      remove.textContent = 'Remover';
      remove.setAttribute('aria-label', `Remover ${file.name}`);
      remove.addEventListener('click', () => {
        files.splice(index, 1);
        renderSelection();
        (list.querySelector('button') || input).focus();
      });
      item.append(description, remove);
      list.append(item);
    });
    const total = files.reduce((sum, file) => sum + file.size, 0);
    find('selection-summary').textContent = files.length ? `${files.length} documento(s) · ${formatSize(total)}` : 'Nenhum documento selecionado.';
    find('clear-selection').hidden = !files.length;
    convertButton.disabled = locked || !available || !files.length;
  }

  function addFiles(incoming) {
    if (locked) return;
    const combined = [...files, ...incoming];
    if (combined.length > maxFiles) return showError(`Selecione no máximo ${maxFiles} documentos.`);
    if (incoming.some(file => !file.name.toLowerCase().endsWith('.docx'))) return showError('Envie somente documentos no formato .docx.');
    if (incoming.some(file => !file.size)) return showError('Um dos documentos está vazio.');
    if (incoming.some(file => file.size > maxFileBytes) || combined.reduce((sum, file) => sum + file.size, 0) > maxTotalBytes) {
      return showError('Os arquivos excedem o limite de tamanho indicado.');
    }
    files = combined;
    showError('');
    renderSelection();
  }

  input.addEventListener('change', () => { addFiles(Array.from(input.files)); input.value = ''; });
  find('clear-selection').addEventListener('click', () => { files = []; renderSelection(); showError(''); });
  const zone = find('drop-zone');
  ['dragenter', 'dragover'].forEach(eventName => zone.addEventListener(eventName, event => {
    event.preventDefault();
    if (!locked) zone.classList.add('dragging');
  }));
  ['dragleave', 'drop'].forEach(eventName => zone.addEventListener(eventName, event => {
    event.preventDefault();
    zone.classList.remove('dragging');
  }));
  zone.addEventListener('drop', event => addFiles(Array.from(event.dataTransfer.files)));
  // Prevent a dropped file outside the target from navigating away from the task.
  window.addEventListener('dragover', event => event.preventDefault());
  window.addEventListener('drop', event => event.preventDefault());

  function reset() {
    pollGeneration += 1;
    clearTimeout(expiryTimer);
    jobId = null;
    remember(null);
    files = [];
    find('job-progress').hidden = true;
    find('results').hidden = true;
    find('job-actions').hidden = true;
    find('retry-status').hidden = true;
    showError('');
    setLocked(false);
    renderSelection();
    input.focus();
  }

  function showResult(job) {
    find('job-progress').hidden = true;
    find('results').hidden = false;
    find('job-actions').hidden = false;
    find('result-summary').textContent = `${job.files.length} PDF(s) · conversão em ${job.seconds.toLocaleString('pt-BR')} s. Download disponível até ${new Date(job.expires_at * 1000).toLocaleTimeString('pt-BR')}.`;
    const archive = find('download-archive');
    archive.hidden = !job.archive_url;
    if (job.archive_url) archive.href = job.archive_url;
    const downloads = find('download-list');
    downloads.replaceChildren();
    job.files.forEach(file => {
      const item = document.createElement('li');
      const link = document.createElement('a');
      link.href = file.url;
      link.textContent = file.name;
      const size = document.createElement('small');
      size.className = 'muted';
      size.textContent = formatSize(file.bytes);
      item.append(link, size);
      downloads.append(item);
    });
    clearTimeout(expiryTimer);
    expiryTimer = setTimeout(() => {
      find('results').hidden = true;
      find('job-actions').hidden = true;
      showError('O prazo para download terminou. Você pode iniciar uma nova conversão.');
      remember(null);
      jobId = null;
      setLocked(false);
    }, Math.max(0, job.expires_at * 1000 - Date.now()));
    find('results-title').focus();
  }

  async function poll() {
    const generation = ++pollGeneration;
    find('retry-status').hidden = true;
    showError('');
    while (jobId && generation === pollGeneration) {
      try {
        const job = await request(`/api/jobs/${jobId}`);
        if (generation !== pollGeneration) return;
        if (job.state === 'completed') return showResult(job);
        if (job.state === 'failed') {
          find('job-progress').hidden = true;
          find('job-actions').hidden = false;
          showError(job.error);
          return;
        }
        find('job-progress').hidden = false;
        find('progress-title').textContent = job.state === 'queued' ? 'Aguardando na fila' : 'Convertendo seus documentos';
        find('progress-message').textContent = job.state === 'queued' ? 'Sua tarefa começará assim que o processamento anterior terminar.' : 'O processamento pode levar alguns segundos. Você pode manter esta página aberta.';
      } catch (error) {
        if (generation !== pollGeneration) return;
        if (error.status === 404 || error.status === 410) { reset(); showError(error.message); return; }
        showError('Não foi possível consultar o andamento. Confira se o servidor continua aberto e tente novamente.');
        find('retry-status').hidden = false;
        return;
      }
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }

  find('conversion-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (locked || !files.length) return;
    setLocked(true);
    showError('');
    find('job-progress').hidden = false;
    find('progress-title').textContent = 'Enviando documentos';
    find('progress-message').textContent = 'Preparando os arquivos para a conversão.';
    find('progress-title').focus();
    const body = new FormData();
    files.forEach(file => body.append('files', file, file.name));
    try {
      const job = await request('/api/jobs/word-to-pdf', { method: 'POST', body });
      jobId = job.id;
      remember(jobId);
      await poll();
    } catch (error) {
      find('job-progress').hidden = true;
      setLocked(false);
      showError(error.message || 'Falha no envio dos documentos. Tente novamente.');
    }
  });

  find('retry-status').addEventListener('click', poll);
  find('new-conversion').addEventListener('click', reset);
  find('delete-job').addEventListener('click', async () => {
    try {
      await request(`/api/jobs/${jobId}`, { method: 'DELETE' });
      reset();
      find('selection-summary').textContent = 'Arquivos excluídos. Você pode selecionar novos documentos.';
    } catch (error) {
      if (error.status === 404 || error.status === 410) { reset(); return; }
      showError(error.message);
    }
  });

  request('/api/status').then(status => {
    available = status.conversion_available;
    convertButton.disabled = locked || !available || !files.length;
    if (!available) showError('O motor de conversão não foi encontrado. Confira a instalação do LibreOffice e reinicie a suíte.');
  }).catch(() => showError('Não foi possível consultar o servidor. Confira se o terminal da suíte está aberto.'));

  try { jobId = sessionStorage.getItem(storageKey); } catch {}
  if (jobId) { setLocked(true); find('job-progress').hidden = false; poll(); }
})();
