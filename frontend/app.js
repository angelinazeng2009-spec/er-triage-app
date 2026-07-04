const siteShell = document.querySelector('.app-shell');
const themeToggle = document.getElementById('themeToggle');
const accentPicker = document.getElementById('accentPicker');
const saveApiKeyButton = document.getElementById('saveApiKey');
const apiKeyInput = document.getElementById('apiKeyInput');
const apiStatus = document.getElementById('apiStatus');
const chatToggle = document.getElementById('chatToggle');
const chatPanel = document.getElementById('chatPanel');
const chatClose = document.getElementById('chatClose');
const chatMessages = document.getElementById('chatMessages');
const sendChat = document.getElementById('sendChat');
const chatInput = document.getElementById('chatInput');
const loadSample = document.getElementById('loadSample');
const recentList = document.getElementById('recentList');
const intakeForm = document.getElementById('intakeForm');
const queueCount = document.getElementById('queueCount');
const activeCases = document.getElementById('activeCases');
const pendingReview = document.getElementById('pendingReview');

const ACCENT_STORAGE_KEY = 'pulsecareAccentColor';
const THEME_STORAGE_KEY = 'pulsecareTheme';
const API_KEY_STORAGE_KEY = 'pulsecareGeminiKey';

const savedAccent = localStorage.getItem(ACCENT_STORAGE_KEY);
const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
const savedKey = localStorage.getItem(API_KEY_STORAGE_KEY);

if (savedAccent) {
  accentPicker.value = savedAccent;
  document.documentElement.style.setProperty('--accent', savedAccent);
}

if (savedTheme) {
  siteShell.dataset.theme = savedTheme;
  themeToggle.textContent = savedTheme === 'dark' ? 'Switch to Light' : 'Switch to Dark';
}

if (savedKey) {
  apiKeyInput.value = savedKey;
  apiStatus.textContent = 'Gemini API key loaded from local storage.';
}

accentPicker.addEventListener('input', (event) => {
  const color = event.target.value;
  document.documentElement.style.setProperty('--accent', color);
  localStorage.setItem(ACCENT_STORAGE_KEY, color);
});

themeToggle.addEventListener('click', () => {
  const nextTheme = siteShell.dataset.theme === 'dark' ? 'light' : 'dark';
  siteShell.dataset.theme = nextTheme;
  localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
  themeToggle.textContent = nextTheme === 'dark' ? 'Switch to Light' : 'Switch to Dark';
});

saveApiKeyButton.addEventListener('click', () => {
  const value = apiKeyInput.value.trim();
  if (!value) {
    apiStatus.textContent = 'Please enter a valid Gemini API key before saving.';
    return;
  }
  localStorage.setItem(API_KEY_STORAGE_KEY, value);
  apiStatus.textContent = 'Gemini API key saved locally.';
});

chatToggle.addEventListener('click', () => {
  chatPanel.classList.toggle('open');
});

chatClose.addEventListener('click', () => {
  chatPanel.classList.remove('open');
});

sendChat.addEventListener('click', () => {
  const text = chatInput.value.trim();
  if (!text) return;
  appendMessage(text, 'user');
  chatInput.value = '';
  appendMessage('I’m here to help with the PulseCare workflow. Ask me about intake, triage, or the dashboard.', 'assistant');
});

chatInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    event.preventDefault();
    sendChat.click();
  }
});

loadSample.addEventListener('click', () => {
  addRecentPatient({
    name: 'María López',
    language: 'Spanish',
    symptoms: 'Dolor de pecho y respiración entrecortada.',
    status: 'ESI-2',
  });
});

intakeForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const name = document.getElementById('patientName').value.trim();
  const language = document.getElementById('patientLanguage').value.trim();
  const symptoms = document.getElementById('patientSymptoms').value.trim();
  if (!name || !language || !symptoms) {
    alert('Please fill in all intake fields before submitting.');
    return;
  }
  addRecentPatient({ name, language, symptoms, status: 'ESI-3' });
  intakeForm.reset();
});

function appendMessage(text, role) {
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;
  bubble.textContent = text;
  chatMessages.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addRecentPatient(patient) {
  const item = document.createElement('div');
  item.className = 'recent-item';
  item.innerHTML = `
    <strong>${patient.name}</strong>
    <p>${patient.language} • ${patient.status}</p>
    <p>${patient.symptoms}</p>
  `;
  const empty = recentList.querySelector('.empty-state');
  if (empty) empty.remove();
  recentList.prepend(item);

  const currentQueue = Number(queueCount.textContent) || 0;
  queueCount.textContent = currentQueue + 1;
}
