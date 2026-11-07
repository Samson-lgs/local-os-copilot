const state = { history: [], messages: [], events: [] };
let selectedRegion = null;
const $ = (id) => document.getElementById(id);

function addMessage(role, text) {
  $('welcome').style.display = 'none';
  const item = document.createElement('article');
  item.className = `message ${role}`;
  item.innerHTML = `<div class="avatar">${role === 'user' ? 'Y' : 'S'}</div><div class="message-body"><div class="message-name">${role === 'user' ? 'You' : 'Sam'}</div><div class="message-content"></div></div>`;
  item.querySelector('.message-content').textContent = text;
  $('messages').appendChild(item);
  item.scrollIntoView({ behavior: 'smooth', block: 'end' });
}

function trace(label, content, ok = true) {
  const empty = document.querySelector('.empty-trace');
  if (empty) empty.remove();
  const item = document.createElement('div');
  item.className = `trace-item ${ok ? 'ok' : 'fail'}`;
  item.innerHTML = `<strong>${ok ? '●' : '×'} ${label}</strong><small>${content || ''}</small>`;
  $('traceList').appendChild(item);
  $('traceList').scrollTop = $('traceList').scrollHeight;
}

function phase(value) { $('phase').textContent = value; }

async function send() {
  const input = $('messageInput');
  const message = input.value.trim();
  if (!message) return;
  input.value = '';
  addMessage('user', message);
  phase('PLANNING');
  trace('Planning', message);
  $('sendButton').disabled = true;
  try {
    phase('ACTING');
    const response = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message, history: state.history }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Local request failed');
    for (const event of data.events || []) trace(event.name, `${event.ok ? 'completed' : 'failed'} · ${event.duration_ms} ms`, event.ok);
    phase('VERIFYING');
    addMessage('assistant', data.reply || 'No response returned.');
    state.history = data.messages || [];
    phase('READY');
  } catch (error) {
    trace('Request failed', error.message, false);
    addMessage('assistant', `Local error: ${error.message}`);
    phase('ERROR');
  } finally { $('sendButton').disabled = false; }
}

async function health() {
  try {
    const response = await fetch('/api/health');
    const data = await response.json();
    $('statusDot').classList.toggle('online', data.online);
    $('statusText').textContent = data.online ? 'Ollama online' : 'Ollama offline';
    $('modelText').textContent = data.model || 'local model';
  } catch { $('statusText').textContent = 'API offline'; }
}

async function captureScreen() {
  $('preview').textContent = 'Capturing locally...';
  try {
    const response = await fetch('/api/screenshot');
    const data = await response.json();
    if (data.image) {
      const image = document.createElement('img');
      image.alt = 'Local screen preview';
      image.src = `data:image/png;base64,${data.image}`;
      image.dataset.screenWidth = data.width;
      image.dataset.screenHeight = data.height;
      image.addEventListener('mousedown', (event) => {
        image.dataset.startX = event.clientX;
        image.dataset.startY = event.clientY;
      });
      image.addEventListener('mouseup', (event) => {
        const rect = image.getBoundingClientRect();
        const scaleX = Number(image.dataset.screenWidth) / rect.width;
        const scaleY = Number(image.dataset.screenHeight) / rect.height;
        const startX = Number(image.dataset.startX || event.clientX);
        const startY = Number(image.dataset.startY || event.clientY);
        const x = Math.max(0, Math.min(startX, event.clientX) - rect.left);
        const y = Math.max(0, Math.min(startY, event.clientY) - rect.top);
        const width = Math.abs(event.clientX - startX);
        const height = Math.abs(event.clientY - startY);
        selectedRegion = { left: Math.round(x * scaleX), top: Math.round(y * scaleY), width: Math.round(width * scaleX), height: Math.round(height * scaleY) };
        $('regionButton').disabled = width < 4 || height < 4;
        $('regionButton').textContent = width >= 4 && height >= 4 ? 'OCR selected region' : 'OCR selection';
      });
      $('preview').replaceChildren(image);
      $('regionButton').disabled = false;
    }
    else throw new Error(data.error || 'Screen capture failed');
  } catch (error) { $('preview').textContent = error.message; }
}

async function ocrSelection() {
  const image = $('preview img');
  if (!image || !selectedRegion) return;
  const response = await fetch('/api/ocr-region', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(selectedRegion) });
  const data = await response.json();
  addMessage('assistant', data.text || data.error || 'No OCR result.');
}

async function recordVoice() {
  const button = $('voiceButton');
  button.classList.add('recording'); button.textContent = 'Recording...'; phase('LISTENING');
  try {
    const response = await fetch('/api/voice', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ seconds: 8 }) });
    const data = await response.json();
    if (data.text && !data.text.startsWith('Error:')) { $('messageInput').value = data.text; send(); }
    else trace('Voice input', data.text || 'No transcription', false);
  } catch (error) { trace('Voice input', error.message, false); }
  button.classList.remove('recording'); button.textContent = 'Push to talk'; phase('READY');
}

async function speakLast() {
  const replies = [...document.querySelectorAll('.message.assistant .message-content')];
  const text = replies.at(-1)?.textContent;
  if (!text) return;
  phase('SPEAKING');
  const response = await fetch('/api/speak', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) });
  const data = await response.json();
  trace('Speech output', data.result || data.error, !String(data.result || '').startsWith('Error:'));
  phase('READY');
}

function exportChat() {
  const text = [...document.querySelectorAll('.message')].map((node) => `${node.querySelector('.message-name').textContent}\n${node.querySelector('.message-content').textContent}`).join('\n\n');
  const blob = new Blob([text], { type: 'text/plain' });
  const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'sam-conversation.txt'; link.click(); URL.revokeObjectURL(link.href);
}

$('sendButton').addEventListener('click', send);
$('messageInput').addEventListener('keydown', (event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(); } });
$('refreshScreen').addEventListener('click', captureScreen);
$('regionButton').addEventListener('click', ocrSelection);
$('voiceButton').addEventListener('click', recordVoice);
$('speakButton').addEventListener('click', speakLast);
$('screenButton').addEventListener('click', () => { $('messageInput').value = 'Read my screen'; $('messageInput').focus(); });
$('knowledgeButton').addEventListener('click', () => { $('messageInput').value = 'Search my local documents'; $('messageInput').focus(); });
$('exportButton').addEventListener('click', exportChat);
$('newChat').addEventListener('click', () => { state.history = []; state.events = []; $('messages').innerHTML = ''; $('traceList').innerHTML = '<div class="empty-trace">Sam\'s plan and tool results will appear here.</div>'; $('welcome').style.display = 'block'; phase('READY'); });
document.querySelectorAll('[data-prompt]').forEach((button) => button.addEventListener('click', () => { $('messageInput').value = button.dataset.prompt; send(); }));
health();
setInterval(health, 30000);
