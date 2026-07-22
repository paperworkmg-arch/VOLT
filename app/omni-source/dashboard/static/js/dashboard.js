/* Omni-Studio Dashboard — Client-side logic */

// === Tab Navigation ===
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', (e) => {
    e.preventDefault();
    const tab = item.dataset.tab;

    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));

    item.classList.add('active');
    document.getElementById('tab-' + tab).classList.add('active');
    document.getElementById('page-title').textContent = item.textContent.trim();

    if (tab === 'sites') loadSites();
    if (tab === 'samples') { loadSampleStats(); searchSamples(); }
    if (tab === 'sampler') loadKits();
    if (tab === 'autopilot') loadAutopilot();
  });
});

// === Init ===
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  refreshAll();
  loadSites();
  loadSampleStats();
  searchSamples();
  loadKits();
  loadAutopilot();
});

// === Task Actions ===
async function runTask(taskId) {
  const res = await fetch(`/api/tasks/${taskId}/run`, { method: 'POST' });
  const data = await res.json();
  if (data.status === 'started') {
    showToast('Task started');
    setTimeout(refreshAll, 2000);
  }
}

async function toggleTask(taskId) {
  await fetch(`/api/tasks/${taskId}/toggle`, { method: 'POST' });
  refreshAll();
}

// === Swarm ===
async function launchSwarm(e) {
  e.preventDefault();
  const objective = document.getElementById('swarm-objective').value;
  const btn = document.getElementById('swarm-btn');
  const result = document.getElementById('swarm-result');

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Swarm running...';
  result.classList.remove('hidden');
  result.textContent = 'Decomposing objective and dispatching agents...';

  try {
    const formData = new FormData();
    formData.append('objective', objective);
    const res = await fetch('/api/swarm/run', { method: 'POST', body: formData });
    const data = await res.json();

    if (data.status === 'completed') {
      let html = `<strong>Swarm Complete</strong> (${data.results?.length || 0} subtasks)\n\n`;
      data.results?.forEach(r => {
        const icon = r.status === 'success' ? '✓' : '✗';
        html += `${icon} [${r.agent}] ${r.task}\n   ${r.result?.substring(0, 300) || 'No output'}\n\n`;
      });
      result.textContent = html;
    } else {
      result.textContent = JSON.stringify(data, null, 2);
    }
  } catch (err) {
    result.textContent = 'Error: ' + err.message;
  }

  btn.disabled = false;
  btn.textContent = '◎ Launch Swarm';
}

// === Plugins ===
async function runPlugin(name) {
  const resultDiv = document.getElementById('plugin-result');
  resultDiv.classList.remove('hidden');
  resultDiv.textContent = `Running plugin "${name}"...`;

  try {
    const res = await fetch(`/api/plugins/${name}/run`, { method: 'POST' });
    const data = await res.json();
    resultDiv.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    resultDiv.textContent = 'Error: ' + err.message;
  }
}

// === Chat ===
async function sendChat(e) {
  e.preventDefault();
  const message = document.getElementById('chat-message').value;
  const provider = document.getElementById('chat-provider').value;
  const messagesDiv = document.getElementById('chat-messages');

  // Add user message
  messagesDiv.innerHTML += `<div class="chat-msg user">${escapeHtml(message)}</div>`;

  // Add loading
  const loadingId = 'loading-' + Date.now();
  messagesDiv.innerHTML += `<div class="chat-msg assistant" id="${loadingId}"><span class="spinner"></span> Thinking...</div>`;
  messagesDiv.scrollTop = messagesDiv.scrollHeight;

  document.getElementById('chat-message').value = '';

  try {
    const formData = new FormData();
    formData.append('message', message);
    formData.append('provider', provider);

    const res = await fetch('/api/chat', { method: 'POST', body: formData });
    const data = await res.json();

    const el = document.getElementById(loadingId);
    if (el) el.textContent = data.response || 'No response';
  } catch (err) {
    const el = document.getElementById(loadingId);
    if (el) el.textContent = 'Error: ' + err.message;
  }

  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// === Refresh ===
async function refreshAll() {
  try {
    const [tasksRes, agentsRes, activityRes, sitesRes, swarmRes, healthRes] = await Promise.all([
      fetch('/api/tasks').then(r => r.json()),
      fetch('/api/agents').then(r => r.json()),
      fetch('/api/activity').then(r => r.json()),
      fetch('/api/sites').then(r => r.json()),
      fetch('/api/swarm/runs').then(r => r.json()),
      fetch('/api/health').then(r => r.json()),
    ]);

    // Update stats
    document.getElementById('stat-agents').textContent = agentsRes.length;
    document.getElementById('stat-tasks').textContent = tasksRes.length;
    document.getElementById('stat-swarm').textContent = swarmRes.length;
    renderSites(sitesRes);

    // Update status indicator + timestamp
    const tsEl = document.getElementById('sys-timestamp');
    if (tsEl) tsEl.textContent = new Date().toLocaleString();
    const dot = document.getElementById('sys-status-dot');
    const statusText = document.getElementById('sys-status-text');
    if (dot && healthRes.status === 'ok') {
      dot.className = 'status-dot green';
      if (statusText) statusText.textContent = 'All systems nominal';
    } else if (dot) {
      dot.className = 'status-dot';
      dot.style.background = 'var(--red)';
      if (statusText) statusText.textContent = 'Connection issue';
    }
  } catch (err) {
    console.error('Refresh failed:', err);
    const dot = document.getElementById('sys-status-dot');
    const statusText = document.getElementById('sys-status-text');
    if (dot) { dot.className = 'status-dot'; dot.style.background = 'var(--red)'; }
    if (statusText) statusText.textContent = 'Connection lost';
  }
}

// === Sites ===
function renderSites(sites) {
  const grid = document.getElementById('sites-grid');
  if (!grid) return;
  if (!sites || sites.length === 0) {
    grid.innerHTML = '<p class="muted">No sites yet. Create one above.</p>';
    return;
  }
  grid.innerHTML = sites.map(s => `
    <div class="site-card">
      <div class="site-header">
        <span class="site-name">${escapeHtml(s.name)}</span>
        <span class="site-status ${s.status || 'draft'}">${s.status || 'draft'}</span>
      </div>
      <div class="site-template">Template: ${escapeHtml(s.template || 'default')}</div>
      <div class="site-meta">Domain: ${escapeHtml(s.domain || '—')}</div>
      <div class="site-actions">
        <a class="btn btn-sm" href="/sites/${escapeHtml(s.name.toLowerCase().replace(/\s+/g, '-'))}/" target="_blank">Open</a>
      </div>
    </div>
  `).join('');
}

async function loadSites() {
  try {
    const res = await fetch('/api/sites');
    const sites = await res.json();
    renderSites(sites);
  } catch (err) {
    console.error('Failed to load sites:', err);
  }
}

// === Sampler / Kits ===
async function loadKits() {
  try {
    const res = await fetch('/api/kits');
    const kits = await res.json();
    renderKits(kits);
  } catch (err) {
    console.error('Failed to load kits:', err);
  }
}

// === Autopilot ===
async function loadAutopilot() {
  try {
    const res = await fetch('/api/autopilot/status');
    const data = await res.json();
    renderAutopilot(data);
  } catch (err) {
    console.error('Failed to load autopilot:', err);
  }
}

function renderAutopilot(data) {
  const dot = document.getElementById('autopilot-dot');
  const state = document.getElementById('autopilot-state');
  if (data.running) {
    dot.className = 'status-dot green';
    state.textContent = 'Autopilot running';
  } else {
    dot.className = 'status-dot';
    dot.style.background = 'var(--red)';
    state.textContent = 'Autopilot stopped';
  }

  const jobsDiv = document.getElementById('autopilot-jobs');
  if (data.jobs?.length) {
    jobsDiv.innerHTML = data.jobs.map(j => `
      <div class="autopilot-job ${j.enabled ? '' : 'disabled'}">
        <div class="job-main">
          <div class="job-info">
            <span class="job-name">${escapeHtml(j.name)}</span>
            <span class="job-meta">${escapeHtml(j.script)} · ${escapeHtml(j.schedule)} · ${j.category}</span>
          </div>
          <div class="job-status">
            <span class="status-pill ${j.last_status || 'pending'}">${j.last_status || 'pending'}</span>
            <span class="job-counts">${j.run_count || 0} runs · ${j.fail_count || 0} fails</span>
          </div>
        </div>
        <div class="job-actions">
          <button class="btn btn-sm" onclick="runAutopilotJob('${escapeHtml(j.name)}')">▶ Run Now</button>
          <button class="btn btn-sm btn-ghost" onclick="toggleAutopilotJob('${escapeHtml(j.name)}')">${j.enabled ? 'Disable' : 'Enable'}</button>
        </div>
        ${j.last_output ? `<div class="job-output">${escapeHtml(j.last_output.slice(0, 300))}${j.last_output.length > 300 ? '...' : ''}</div>` : ''}
      </div>
    `).join('');
  } else {
    jobsDiv.innerHTML = '<p class="muted">No jobs configured.</p>';
  }

  const runsDiv = document.getElementById('autopilot-runs');
  if (data.recent_runs?.length) {
    runsDiv.innerHTML = data.recent_runs.map(r => `
      <div class="autopilot-run ${r.status}">
        <span class="run-time">${r.started_at ? r.started_at.slice(0, 19).replace('T', ' ') : ''}</span>
        <span class="run-name">${escapeHtml(r.job_name)}</span>
        <span class="status-pill ${r.status}">${r.status}</span>
        <span class="run-duration">${r.duration_ms}ms</span>
      </div>
    `).join('');
  } else {
    runsDiv.innerHTML = '<p class="muted">No runs yet.</p>';
  }
}

async function startAutopilot() {
  await fetch('/api/autopilot/start', { method: 'POST' });
  showToast('Autopilot started', 'success');
  loadAutopilot();
}

async function stopAutopilot() {
  await fetch('/api/autopilot/stop', { method: 'POST' });
  showToast('Autopilot stopped');
  loadAutopilot();
}

async function runAutopilotJob(name) {
  showToast(`Running ${name}...`);
  const res = await fetch(`/api/autopilot/jobs/${encodeURIComponent(name)}/run`, { method: 'POST' });
  const data = await res.json();
  showToast(`${name}: ${data.status}`, data.status === 'success' ? 'success' : 'error');
  loadAutopilot();
}

async function toggleAutopilotJob(name) {
  await fetch(`/api/autopilot/jobs/${encodeURIComponent(name)}/toggle`, { method: 'POST' });
  loadAutopilot();
}

async function runAutopilotCycle() {
  const jobs = document.querySelectorAll('.autopilot-job');
  if (!jobs.length) return;
  showToast('Running all enabled jobs...');
  for (const jobEl of jobs) {
    if (jobEl.classList.contains('disabled')) continue;
    const name = jobEl.querySelector('.job-name')?.textContent;
    if (name) await runAutopilotJob(name);
  }
  loadAutopilot();
}

function renderKits(kits) {
  const grid = document.getElementById('kits-grid');
  if (!grid) return;
  if (!kits || kits.length === 0) {
    grid.innerHTML = '<p class="muted">No kits yet. Create one above.</p>';
    return;
  }
  grid.innerHTML = kits.map(k => `
    <div class="kit-card">
      <div class="kit-header">
        <span class="kit-name">${escapeHtml(k.name)}</span>
        <span class="kit-type">${escapeHtml(k.layout_type)}</span>
      </div>
      <div class="kit-desc">${escapeHtml(k.description || 'No description')}</div>
      <div class="kit-meta">${k.sample_count} samples · ${k.created_at ? k.created_at.slice(0, 16).replace('T', ' ') : ''}</div>
      <div class="kit-actions">
        <button class="btn btn-sm" onclick="exportKit(${k.id})">📦 Export SFZ</button>
        <button class="btn btn-sm" onclick="uploadKitDrive(${k.id})">☁ Upload to Drive</button>
        <button class="btn btn-sm btn-ghost" onclick="deleteKit(${k.id})">🗑 Delete</button>
      </div>
      ${k.drive_url ? `<div class="kit-drive"><a href="${escapeHtml(k.drive_url)}" target="_blank">Open in Drive ↗</a></div>` : ''}
    </div>
  `).join('');
}

async function createKit(e) {
  e.preventDefault();
  const name = document.getElementById('kit-name').value;
  const description = document.getElementById('kit-desc').value;
  const layout_type = document.getElementById('kit-layout').value;
  const sample_ids = document.getElementById('kit-samples').value;

  const btn = e.submitter;
  btn.disabled = true;
  btn.textContent = 'Creating...';

  try {
    const formData = new FormData();
    formData.append('name', name);
    formData.append('description', description);
    formData.append('layout_type', layout_type);
    formData.append('sample_ids', sample_ids);

    const res = await fetch('/api/kits', { method: 'POST', body: formData });
    const data = await res.json();
    if (data.kit_id) {
      showToast(`Kit "${name}" created`, 'success');
      document.getElementById('kit-name').value = '';
      document.getElementById('kit-desc').value = '';
      document.getElementById('kit-samples').value = '';
      loadKits();
    } else {
      showToast('Failed to create kit', 'error');
    }
  } catch (err) {
    showToast('Error: ' + err.message, 'error');
  }

  btn.disabled = false;
  btn.textContent = '+ Create Kit';
}

async function exportKit(kitId) {
  showToast('Exporting kit...');
  try {
    const formData = new FormData();
    formData.append('fmt', 'sfz');
    const res = await fetch(`/api/kits/${kitId}/export`, { method: 'POST', body: formData });
    const data = await res.json();
    if (data.zip) {
      showToast(`Kit exported: ${data.samples_copied} samples`, 'success');
      // Trigger download
      const a = document.createElement('a');
      a.href = data.zip;
      a.download = data.zip.split('/').pop();
      a.click();
    } else {
      showToast('Export failed: ' + (data.error || 'unknown'), 'error');
    }
  } catch (err) {
    showToast('Export error: ' + err.message, 'error');
  }
}

async function uploadKitDrive(kitId) {
  showToast('Uploading kit to Drive...');
  try {
    const res = await fetch(`/api/kits/${kitId}/upload-drive`, { method: 'POST' });
    const data = await res.json();
    if (data.url) {
      showToast('Uploaded to Drive!', 'success');
      loadKits();
    } else {
      showToast('Upload failed: ' + (data.error || 'unknown'), 'error');
    }
  } catch (err) {
    showToast('Upload error: ' + err.message, 'error');
  }
}

async function deleteKit(kitId) {
  if (!confirm('Delete this kit?')) return;
  try {
    const res = await fetch(`/api/kits/${kitId}`, { method: 'DELETE' });
    if (res.ok) {
      showToast('Kit deleted', 'success');
      loadKits();
    }
  } catch (err) {
    showToast('Delete error: ' + err.message, 'error');
  }
}

// === Toast ===
function showToast(msg, type = 'info') {
  const toast = document.createElement('div');
  toast.className = 'toast ' + type;
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// === Theme Toggle ===
function initTheme() {
  const saved = localStorage.getItem('omni-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('omni-theme', next);
}

// === Keyboard Shortcuts ===
document.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if (e.key === 'r' || e.key === 'R') refreshAll();
  if (e.key === 't' || e.key === 'T') document.querySelector('[data-tab="tasks"]')?.click();
  if (e.key === 's' || e.key === 'S') document.querySelector('[data-tab="swarm"]')?.click();
  if (e.key === 'c' || e.key === 'C') document.querySelector('[data-tab="chat"]')?.click();
  if (e.key === '1') document.querySelector('[data-tab="dashboard"]')?.click();
  if (e.key === '2') document.querySelector('[data-tab="tasks"]')?.click();
  if (e.key === '3') document.querySelector('[data-tab="swarm"]')?.click();
  if (e.key === '4') document.querySelector('[data-tab="plugins"]')?.click();
  if (e.key === '5') document.querySelector('[data-tab="sites"]')?.click();
  if (e.key === '6') document.querySelector('[data-tab="samples"]')?.click();
  if (e.key === '7') document.querySelector('[data-tab="chat"]')?.click();
});

// === Utils ===
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// === Sample Library ===
let slPage = 0;
const slPageSize = 50;
let slDebounceTimer = null;

async function loadSampleStats() {
  try {
    const res = await fetch('/api/samples/stats');
    const s = await res.json();
    document.getElementById('sl-total').textContent = s.total_samples?.toLocaleString() || '0';
    document.getElementById('sl-analyzed').textContent = s.analyzed?.toLocaleString() || '0';
    document.getElementById('sl-size').textContent = s.total_size_mb > 1024
      ? (s.total_size_mb / 1024).toFixed(1) + ' GB' : (s.total_size_mb || 0) + ' MB';
    document.getElementById('sl-tempo').textContent = s.avg_tempo ? s.avg_tempo + ' BPM' : '—';

    // Populate key filter
    const keySelect = document.getElementById('sl-key-filter');
    const keysRes = await fetch('/api/samples/keys');
    const keys = await keysRes.json();
    const currentKey = keySelect.value;
    keySelect.innerHTML = '<option value="">All Keys</option>';
    keys.forEach(k => {
      keySelect.innerHTML += `<option value="${k}" ${k === currentKey ? 'selected' : ''}>${k}</option>`;
    });
  } catch (e) { console.error('Stats load failed:', e); }
}

function debounceSearch() {
  clearTimeout(slDebounceTimer);
  slDebounceTimer = setTimeout(() => { slPage = 0; searchSamples(); }, 300);
}

async function searchSamples() {
  const q = document.getElementById('sl-search').value;
  const key = document.getElementById('sl-key-filter').value;
  const tempoMin = document.getElementById('sl-tempo-min').value || 0;
  const tempoMax = document.getElementById('sl-tempo-max').value || 999;
  const sampleType = document.getElementById('sl-type-filter').value;

  const params = new URLSearchParams({
    q, key, tempo_min: tempoMin, tempo_max: tempoMax,
    sample_type: sampleType, limit: slPageSize, offset: slPage * slPageSize
  });

  try {
    const res = await fetch(`/api/samples?${params}`);
    const data = await res.json();
    renderSamples(data);
  } catch (e) { console.error('Search failed:', e); }
}

function renderSamples(data) {
  const body = document.getElementById('sl-body');
  const empty = document.getElementById('sl-empty');
  const count = document.getElementById('sl-count');
  const pageInfo = document.getElementById('sl-page-info');

  count.textContent = `${data.total} samples`;
  const totalPages = Math.ceil(data.total / slPageSize);
  pageInfo.textContent = totalPages > 0 ? `Page ${slPage + 1} of ${totalPages}` : '';

  if (!data.samples || data.samples.length === 0) {
    body.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');

  body.innerHTML = data.samples.map(s => {
    const dur = s.duration > 0 ? formatDuration(s.duration) : '—';
    const tempo = s.tempo > 0 ? Math.round(s.tempo) + ' BPM' : '—';
    const key = s.key_full || '—';
    const size = s.size_mb > 1024 ? (s.size_mb / 1024).toFixed(1) + ' GB' : s.size_mb + ' MB';
    const source = (s.directory || '').split('/').pop() || '—';
    const analyzed = s.analyzed ? '' : ' <span class="badge pending">pending</span>';
    return `<tr>
      <td title="ID: ${s.id}"><code>#${s.id}</code> ${escapeHtml(s.filename)}${analyzed}</td>
      <td><span class="sl-key-badge">${key}</span></td>
      <td>${tempo}</td>
      <td><span class="badge ${s.sample_type}">${s.sample_type}</span></td>
      <td>${dur}</td>
      <td>${size}</td>
      <td title="${escapeHtml(s.directory || '')}">${escapeHtml(source)}</td>
      <td class="actions">
        <button class="btn btn-sm" onclick="addSampleToKit(${s.id})" title="Add to kit">+</button>
        <button class="btn btn-sm" onclick="exportSample(${s.id})">☁</button>
      </td>
    </tr>`;
  }).join('');
}

function addSampleToKit(sampleId) {
  const input = document.getElementById('kit-samples');
  const existing = input.value.split(',').map(s => s.trim()).filter(Boolean);
  if (!existing.includes(String(sampleId))) {
    existing.push(sampleId);
    input.value = existing.join(', ');
    showToast(`Sample #${sampleId} added to kit list`, 'success');
    document.querySelector('[data-tab="sampler"]')?.click();
  } else {
    showToast(`Sample #${sampleId} already in list`);
  }
}

function formatDuration(secs) {
  if (!secs || secs <= 0) return '—';
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return m + ':' + String(s).padStart(2, '0');
}

function nextPage() { slPage++; searchSamples(); }
function prevPage() { if (slPage > 0) { slPage--; searchSamples(); } }

async function startScan() {
  showToast('Scanning audio files...');
  try {
    const res = await fetch('/api/samples/scan', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'started') {
      showToast(`Scan started (${data.scan_id}) — finding all audio files...`);
      // Poll for completion
      const poll = setInterval(async () => {
        const hist = await fetch('/api/samples/scan-history').then(r => r.json());
        const latest = hist[0];
        if (latest && latest.status === 'completed') {
          clearInterval(poll);
          showToast(`Scan complete: ${latest.files_found} files found`);
          loadSampleStats();
          searchSamples();
        }
      }, 5000);
    }
  } catch (e) { showToast('Scan failed: ' + e.message); }
}

async function startAnalyze() {
  showToast('Starting analysis (key/tempo extraction)...');
  try {
    const res = await fetch('/api/samples/analyze', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'started') {
      showToast(`Analyzing ${data.count} samples for key and tempo...`);
      // Poll for completion
      const poll = setInterval(async () => {
        const stats = await fetch('/api/samples/stats').then(r => r.json());
        if (stats.unanalyzed === 0) {
          clearInterval(poll);
          showToast('Analysis complete!');
          loadSampleStats();
          searchSamples();
        }
      }, 10000);
    } else {
      showToast(data.status === 'nothing_to_analyze' ? 'All samples already analyzed!' : data.status);
    }
  } catch (e) { showToast('Analyze failed: ' + e.message); }
}

async function exportSample(id) {
  showToast('Uploading to Google Drive...');
  try {
    const formData = new FormData();
    formData.append('sample_id', id);
    const res = await fetch('/api/samples/export', { method: 'POST', body: formData });
    const data = await res.json();
    if (data.status === 'uploaded') {
      showToast('Uploaded to Drive!');
    } else {
      showToast('Upload failed: ' + (data.error || 'unknown'));
    }
  } catch (e) { showToast('Upload error: ' + e.message); }
}

// Auto-refresh every 30s
setInterval(refreshAll, 30000);
