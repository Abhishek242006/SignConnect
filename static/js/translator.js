// Translator page: stabilises predictions, builds sentences, speaks them.
const $ = (id) => document.getElementById(id);
const STABLE_FRAMES = 6, WINDOW = 8, ABSENT_RESET = 8;
const TR = {
  hi: {"Hello":"नमस्ते","Thank You":"धन्यवाद","Yes":"हाँ","No":"नहीं","Help":"मदद","Please":"कृपया","Stop":"रुको","Good":"अच्छा","Bad":"बुरा","Water":"पानी","Food":"खाना","Emergency":"आपातकाल","Doctor":"डॉक्टर","Call":"फ़ोन करो","Sorry":"माफ़ कीजिए","I":"मैं","You":"आप"},
  ta: {"Hello":"வணக்கம்","Thank You":"நன்றி","Yes":"ஆம்","No":"இல்லை","Help":"உதவி","Please":"தயவுசெய்து","Stop":"நிறுத்து","Good":"நல்லது","Bad":"மோசம்","Water":"தண்ணீர்","Food":"உணவு","Emergency":"அவசரம்","Doctor":"மருத்துவர்","Call":"அழை","Sorry":"மன்னிக்கவும்","I":"நான்","You":"நீங்கள்"},
  es: {"Hello":"Hola","Thank You":"Gracias","Yes":"Sí","No":"No","Help":"Ayuda","Please":"Por favor","Stop":"Alto","Good":"Bien","Bad":"Mal","Water":"Agua","Food":"Comida","Emergency":"Emergencia","Doctor":"Doctor","Call":"Llamar","Sorry":"Lo siento","I":"Yo","You":"Tú"},
  fr: {"Hello":"Bonjour","Thank You":"Merci","Yes":"Oui","No":"Non","Help":"Aide","Please":"S'il vous plaît","Stop":"Arrêtez","Good":"Bien","Bad":"Mauvais","Water":"Eau","Food":"Nourriture","Emergency":"Urgence","Doctor":"Médecin","Call":"Appeler","Sorry":"Désolé","I":"Je","You":"Vous"}
};
const EMERGENCY = new Set(["Help", "Emergency"]);

let words = [], recent = [], lastAdded = null, absent = 0, paused = false, cam = null;
let activeUtterance = null, emergencySpoken = false;

function showToast(msg) {
  const note = document.createElement('div');
  note.className = 'toast';
  note.textContent = msg;
  document.body.appendChild(note);
  setTimeout(() => note.remove(), 1800);
}

function formatSentence(ws) {
  if (!ws.length) return '';
  let out = ws.map((w, i) => (w === 'I' ? 'I' : (i === 0 ? w : w.toLowerCase())));
  let s = out.join(' ');
  s = s.charAt(0).toUpperCase() + s.slice(1);
  return s + (ws.some(w => EMERGENCY.has(w)) ? '!' : '.');
}
function render() { $('sentence').textContent = words.length ? formatSentence(words) : '(signs will appear here)'; }

function spokenText(lang, sourceWords = words) {
  const code = lang.slice(0, 2);
  return code === 'en' ? formatSentence(sourceWords) : sourceWords.map(w => TR[code][w] || w).join(' ');
}
let VOICES = [];
const loadVoices = () => { VOICES = window.speechSynthesis ? speechSynthesis.getVoices() : []; };
function voiceFor(lang) {
  const l = lang.toLowerCase(), code = l.slice(0, 2);
  return VOICES.find(v => v.lang.replace('_', '-').toLowerCase() === l) ||
         VOICES.find(v => v.lang.toLowerCase().startsWith(code)) || null;
}
function langName() { return $('lang').selectedOptions[0].textContent; }
function checkVoice() {
  const lang = $('lang').value, ok = lang.startsWith('en') || !!voiceFor(lang);
  $('speechMsg').hidden = ok;
  if (!ok) $('speechMsg').textContent = 'No ' + langName() + ' voice is installed on this device, so an online voice will be used ' +
    '(internet needed; only the sentence text is sent, never the camera). For offline speech use Microsoft Edge or add the voice in Windows Settings → Time & language → Speech.';
  return ok;
}
async function onlineSpeak(text, lang) {
  try {
    const r = await fetch('/api/tts?lang=' + lang.slice(0, 2) + '&text=' + encodeURIComponent(text));
    if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.error || ('server error ' + r.status)); }
    const audio = new Audio(URL.createObjectURL(await r.blob()));
    await audio.play();
  } catch (e) { $('speechMsg').hidden = false; $('speechMsg').textContent = '⚠ ' + e.message; }
}
function speak(text, lang) {
  loadVoices();
  const v = voiceFor(lang);
  if (!lang.startsWith('en') && !v) { checkVoice(); onlineSpeak(text, lang); return; }
  if (!('speechSynthesis' in window)) { alert('Speech is not supported in this browser.'); return; }
  if (activeUtterance) {
    activeUtterance.replaced = true;
    speechSynthesis.cancel();
  }
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang; if (v) u.voice = v;
  u.onerror = (e) => {
    if (u.replaced || e.error === 'interrupted' || e.error === 'canceled') return;
    $('speechMsg').hidden = false; $('speechMsg').textContent = 'Speech error: ' + e.error;
  };
  u.onend = () => { if (activeUtterance === u) activeUtterance = null; };
  activeUtterance = u;
  speechSynthesis.speak(u);
}
if ('speechSynthesis' in window) { loadVoices(); speechSynthesis.onvoiceschanged = () => { loadVoices(); checkVoice(); }; }
$('lang').onchange = checkVoice;
async function save() {
  if (!words.length) return;
  await fetch('/api/history', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sentence: formatSentence(words) }) });
}

function updateStatus(pillClass, text) {
  const statusEl = $('camStatus');
  statusEl.className = 'status-pill ' + pillClass;
  statusEl.textContent = text;
}

function onResult(d) {
  if (d.error) { updateStatus('warning', '⚠ ' + d.error); return; }
  updateStatus(d.hand_detected ? 'success' : 'neutral', d.hand_detected ? 'Hand detected' : 'Camera running – show your hand to the camera');
  $('modelWarn').hidden = d.model_loaded;
  $('confBar').style.width = Math.round(d.confidence * 100) + '%';
  $('confText').textContent = Math.round(d.confidence * 100) + '%';
  if (!d.hand_detected) {
    $('gesture').textContent = '—'; $('stateText').textContent = '(no hand detected)';
    recent = []; if (++absent >= ABSENT_RESET) lastAdded = null; return;
  }
  absent = 0;
  if (!d.word) { $('gesture').textContent = 'Unknown'; $('stateText').textContent = '(low confidence – not added)'; recent.push(null); }
  else { $('gesture').textContent = d.word; $('stateText').textContent = ''; recent.push(d.word); }
  recent = recent.slice(-WINDOW);
  $('emergency').hidden = !(d.word && d.emergency);
  if (!d.word || !d.emergency) emergencySpoken = false;
  if (d.word && d.emergency && !emergencySpoken) {
    emergencySpoken = true;
    speak(d.word === 'Help' ? 'Help needed' : 'Emergency', 'en-US');
  }
  if (d.word && d.word !== lastAdded && recent.filter(w => w === d.word).length >= STABLE_FRAMES) {
    words.push(d.word); lastAdded = d.word; render();
  }
}

fetch('/api/status').then(r => r.json()).then(st => {
  $('modelWarn').hidden = st.model_loaded;
  if (!st.mediapipe_ok) { $('modelWarn').hidden = false; $('modelWarn').textContent = '⚠ ' + st.fix; }
});
$('startBtn').onclick = async () => {
  try {
    cam = cam || new SignCamera($('video'), $('overlay'), onResult);
    await cam.start();
    updateStatus('success', 'Camera running – show your hand');
    $('startBtn').disabled = true; $('pauseBtn').disabled = false;
  } catch (e) { updateStatus('warning', 'Could not open the camera: ' + e.message); }
};
function togglePause() {
  if (!cam || !cam.running) return;
  paused = !paused; cam.setPaused(paused);
  $('pauseBtn').textContent = paused ? 'Resume' : 'Pause';
  updateStatus(paused ? 'neutral' : 'success', paused ? 'Paused' : 'Camera running – show your hand');
}
async function clearAll() { await save(); words = []; lastAdded = null; recent = []; render(); }
$('pauseBtn').onclick = togglePause;
$('clearBtn').onclick = clearAll;
$('undoBtn').onclick = () => { words.pop(); lastAdded = null; render(); };
$('speakBtn').onclick = () => {
  const detected = $('gesture').textContent.trim();
  const word = detected && detected !== '—' && detected !== 'Unknown' ? detected : words[words.length - 1];
  if (!word) {
    $('speechMsg').hidden = false;
    $('speechMsg').textContent = 'No recognized word to speak yet. Start the camera and show a supported sign, or add a word to the sentence.';
    return;
  }
  $('speechMsg').hidden = true;
  speak(spokenText($('lang').value, [word]), $('lang').value);
};
$('speakSentenceBtn').onclick = async () => {
  if (!words.length) {
    $('speechMsg').hidden = false;
    $('speechMsg').textContent = 'Add a recognized word to the sentence before speaking it.';
    return;
  }
  $('speechMsg').hidden = true;
  speak(spokenText($('lang').value), $('lang').value);
  await save();
};
$('copyWordBtn').onclick = async () => {
  const text = $('gesture').textContent.trim();
  if (!text || text === '—') return;
  await navigator.clipboard.writeText(text);
  showToast('Word copied');
};
$('addWordBtn').onclick = () => {
  const text = $('gesture').textContent.trim();
  if (!text || text === '—') return;
  words.push(text);
  render();
  showToast('Added to sentence');
};
$('copySentenceBtn').onclick = async () => {
  const text = $('sentence').textContent.trim();
  if (!text || text === '(signs will appear here)') return;
  await navigator.clipboard.writeText(text);
  showToast('Sentence copied');
};
$('clearResultBtn').onclick = () => {
  $('gesture').textContent = '—';
  $('stateText').textContent = '';
  $('confText').textContent = '0%';
  $('confBar').style.width = '0%';
};
document.addEventListener('keydown', (e) => {
  if (['SELECT', 'INPUT', 'TEXTAREA'].includes(document.activeElement.tagName) || document.activeElement.tagName === 'BUTTON') return;
  if (e.code === 'Space') { e.preventDefault(); togglePause(); }
  else if (e.key === 's') $('speakBtn').click(); else if (e.key === 'c') clearAll();
});
