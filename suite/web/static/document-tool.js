(() => {
  'use strict';
  const root = document.getElementById('converter');
  const find = id => document.getElementById(id);
  const input = find('file-input');
  const list = find('file-list');
  const convertButton = find('convert-button');
  const errorMessage = find('error-message');
  const operation = root.dataset.operation;
  const storageKey = operation === 'word-to-pdf' ? 'suite.wordToPdf.job' : `suite.${operation}.job`;
  const extensions = input.accept.split(',');
  const minFiles = Number(root.dataset.minFiles);
  const canReorder = root.dataset.reorder === 'true';
  let files = [];
  let jobId = null;
  let locked = false;
  let engineAvailable = true;
  let pollGeneration = 0;
  let expiryTimer = null;
  let drag = null;
  let dragFrame = null;
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
    finishDrag(false);
    locked = value;
    find('file-controls').disabled = value;
    updateAvailability();
  }

  function updateAvailability() {
    const needsEngine = operation === 'word-to-pdf' || files.some(file => file.name.toLowerCase().endsWith('.docx'));
    const available = !needsEngine || engineAvailable;
    convertButton.disabled = locked || !available || files.length < minFiles;
    const warning = find('engine-message');
    warning.hidden = available;
    warning.textContent = available ? '' : 'O LibreOffice não foi encontrado para converter os arquivos Word. Confira a instalação e reinicie a suíte.';
  }

  function reorderFile(index, target, direction = null) {
    if (locked || !canReorder || target < 0 || target >= files.length || index === target) return;
    const [file] = files.splice(index, 1);
    files.splice(target, 0, file);
    renderSelection();
    const row = list.children[target];
    const buttons = Array.from(row.querySelectorAll('button'));
    const focus = direction === null ? row : (buttons.find(button => button.dataset.direction === String(direction) && !button.disabled) || buttons.find(button => !button.disabled));
    focus.focus({ preventScroll: true });
    row.scrollIntoView({ block: 'nearest' });
    find('selection-summary').textContent = `Ordem atualizada: ${files[target].name} está na posição ${target + 1} de ${files.length}.`;
  }

  function clearDropMarkers() {
    for (const row of list.children) row.classList.remove('drop-before', 'drop-after');
  }

  function updateDragTarget() {
    if (!drag || !drag.active) return;
    const bounds = list.getBoundingClientRect();
    drag.inside = drag.x >= bounds.left && drag.x <= bounds.right && drag.y >= bounds.top && drag.y <= bounds.bottom;
    clearDropMarkers();
    if (!drag.inside) return;
    const rows = Array.from(list.children);
    let boundary = rows.findIndex(row => {
      const rect = row.getBoundingClientRect();
      return drag.y < rect.top + rect.height / 2;
    });
    if (boundary === -1) boundary = rows.length;
    drag.target = boundary > drag.index ? boundary - 1 : boundary;
    if (drag.target !== drag.index) {
      if (boundary === rows.length) rows.at(-1).classList.add('drop-after');
      else rows[boundary].classList.add('drop-before');
    }
  }

  function scrollWhileDragging() {
    if (!drag || !drag.active) return;
    const bounds = list.getBoundingClientRect();
    if (drag.x >= bounds.left && drag.x <= bounds.right && drag.y >= bounds.top && drag.y <= bounds.bottom) {
      const distance = drag.y < bounds.top + 40 ? -8 : drag.y > bounds.bottom - 40 ? 8 : 0;
      if (distance) list.scrollTop += distance;
    }
    updateDragTarget();
    dragFrame = requestAnimationFrame(scrollWhileDragging);
  }

  function finishDrag(commit) {
    if (!drag) return;
    const finished = drag;
    drag = null;
    cancelAnimationFrame(dragFrame);
    clearDropMarkers();
    finished.row.classList.remove('is-dragging');
    root.classList.remove('is-reordering');
    if (list.hasPointerCapture(finished.pointerId)) list.releasePointerCapture(finished.pointerId);
    if (commit && finished.active && finished.inside) reorderFile(finished.index, finished.target);
  }

  list.addEventListener('pointerdown', event => {
    if (locked || !canReorder || files.length < 2 || !event.isPrimary || event.button !== 0 || drag) return;
    if (event.target.closest('button, a, input')) return;
    if (event.pointerType !== 'mouse' && !event.target.closest('.drag-handle')) return;
    const row = event.target.closest('li');
    if (!row || row.parentElement !== list) return;
    event.preventDefault();
    const index = Array.from(list.children).indexOf(row);
    drag = { pointerId: event.pointerId, row, index, target: index, startX: event.clientX, startY: event.clientY,
      x: event.clientX, y: event.clientY, active: false, inside: false };
    list.setPointerCapture(event.pointerId);
  });
  list.addEventListener('pointermove', event => {
    if (!drag || event.pointerId !== drag.pointerId) return;
    drag.x = event.clientX;
    drag.y = event.clientY;
    if (!drag.active && Math.hypot(drag.x - drag.startX, drag.y - drag.startY) >= 6) {
      drag.active = true;
      drag.row.classList.add('is-dragging');
      root.classList.add('is-reordering');
      dragFrame = requestAnimationFrame(scrollWhileDragging);
    }
    updateDragTarget();
  });
  list.addEventListener('pointerup', event => {
    if (!drag || event.pointerId !== drag.pointerId) return;
    drag.x = event.clientX;
    drag.y = event.clientY;
    updateDragTarget();
    finishDrag(true);
  });
  for (const type of ['pointercancel', 'lostpointercapture']) {
    list.addEventListener(type, event => { if (drag && event.pointerId === drag.pointerId) finishDrag(false); });
  }
  window.addEventListener('blur', () => finishDrag(false));
  window.addEventListener('keydown', event => {
    if (event.key === 'Escape' && drag) { finishDrag(false); event.preventDefault(); }
  });

  function renderSelection() {
    finishDrag(false);
    list.replaceChildren();
    files.forEach((file, index) => {
      const item = document.createElement('li');
      item.tabIndex = -1;
      if (canReorder) {
        item.className = 'reorderable';
        const handle = document.createElement('span');
        handle.className = 'drag-handle';
        handle.textContent = '⠿';
        handle.title = 'Segure e arraste para reordenar';
        handle.setAttribute('aria-hidden', 'true');
        item.append(handle);
      }
      const description = document.createElement('span');
      description.className = 'file-description';
      const name = document.createElement('span');
      name.textContent = canReorder ? `${index + 1}. ${file.name}` : file.name;
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
      const actions = document.createElement('span');
      actions.className = 'file-actions';
      if (canReorder) {
        for (const direction of [-1, 1]) {
          const move = document.createElement('button');
          move.type = 'button';
          move.className = 'order-button';
          move.dataset.direction = direction;
          move.textContent = direction === -1 ? '↑' : '↓';
          move.setAttribute('aria-label', `Mover ${file.name} para ${direction === -1 ? 'cima' : 'baixo'}`);
          move.disabled = direction === -1 ? index === 0 : index === files.length - 1;
          move.addEventListener('click', () => reorderFile(index, index + direction, direction));
          actions.append(move);
        }
      }
      actions.append(remove);
      item.append(description, actions);
      list.append(item);
    });
    const total = files.reduce((sum, file) => sum + file.size, 0);
    find('selection-summary').textContent = files.length ? `${files.length} documento(s) · ${formatSize(total)}` : 'Nenhum documento selecionado.';
    find('clear-selection').hidden = !files.length;
    find('empty-selection').hidden = Boolean(files.length);
    updateAvailability();
  }

  function addFiles(incoming) {
    if (locked) return;
    const combined = [...files, ...incoming];
    if (combined.length > maxFiles) return showError(`Selecione no máximo ${maxFiles} documentos.`);
    if (incoming.some(file => !extensions.some(extension => file.name.toLowerCase().endsWith(extension)))) {
      return showError(`Formatos aceitos nesta ferramenta: ${extensions.join(', ')}.`);
    }
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
    const pageCount = job.pages === null ? '' : ` · ${job.pages} página(s)`;
    find('result-summary').textContent = `${job.files.length} PDF(s)${pageCount} · processamento em ${job.seconds.toLocaleString('pt-BR')} s. Download disponível até ${new Date(job.expires_at * 1000).toLocaleTimeString('pt-BR')}.`;
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
      showError('O prazo para download terminou. Você pode enviar os documentos novamente.');
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
        find('progress-title').textContent = job.state === 'queued' ? 'Aguardando na fila' : root.dataset.progress;
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
    if (locked || convertButton.disabled || files.length < minFiles) return;
    setLocked(true);
    showError('');
    find('job-progress').hidden = false;
    find('progress-title').textContent = 'Enviando documentos';
    find('progress-message').textContent = 'Preparando os arquivos para o processamento.';
    find('progress-title').focus();
    const body = new FormData();
    files.forEach(file => body.append('files', file, file.name));
    try {
      const job = await request(`/api/jobs/${operation}`, { method: 'POST', body });
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
    engineAvailable = status.conversion_available;
    updateAvailability();
  }).catch(() => showError('Não foi possível consultar o servidor. Confira se o terminal da suíte está aberto.'));

  try { jobId = sessionStorage.getItem(storageKey); } catch {}
  if (jobId) { setLocked(true); find('job-progress').hidden = false; poll(); }
})();
