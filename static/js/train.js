// In-browser data collection + training. Samples are saved on this computer only.
const $ = (id) => document.getElementById(id);
const TARGET = 150, MIN = 10;
let recording = false, cam = null, counts = {};
$('recTarget').textContent = TARGET;

function current() { return $('signSel').value; }
function showErr(m) { $('err').hidden = !m; $('err').textContent = m || ''; }
function refreshSign() {
  const opt = $('signSel').selectedOptions[0];
  const vid = opt.dataset.video;
  $('refVid').hidden = !vid; $('refImg').hidden = !!vid;
  if (vid) { $('refVid').src = vid; $('refVid').play().catch(() => {}); } else $('refImg').src = opt.dataset.img;
  updateCount(counts[current()] || 0);
}
function updateCount(n) {
  $('recCount').textContent = n; $('recBar').style.width = Math.min(100, n / TARGET * 100) + '%';
  if (n >= TARGET && recording) toggleRec();
}
function renderStats() {
  const rows = window.SIGNS.map(s => {
    const n = counts[s.word] || 0;
    const st = n >= TARGET ? '✅ good' : n >= MIN ? '🟡 ok – more is better' : n > 0 ? '🔴 too few' : '⚪ none';
    return `<tr><td>${s.word}</td><td>${n}</td><td>${st}</td></tr>`;
  });
  $('stats').innerHTML = '<tr><th>Sign</th><th>Samples</th><th>Status</th></tr>' + rows.join('');
}
async function loadCounts() { counts = (await (await fetch('/api/dataset')).json()).counts; renderStats(); refreshSign(); }

function onResult(d) {
  if (d.error) { showErr(d.error); return; }
  showErr('');
  $('camStatus').textContent = d.hand_detected ? (recording ? 'Recording…' : 'Hand detected.') : 'No hand detected – show your hand.';
  if (d.saved) { counts[d.label || current()] = d.count; updateCount(d.count); renderStats(); }
}
function toggleRec() {
  recording = !recording;
  $('recBtn').textContent = recording ? '■ Stop' : '● Record';
}
$('signSel').onchange = () => { if (recording) toggleRec(); refreshSign(); };
$('recBtn').onclick = toggleRec;
$('startBtn').onclick = async () => {
  try {
    cam = new SignCamera($('video'), $('overlay'), onResult, 10, '/api/collect',
                         () => ({ label: current(), record: recording }));
    await cam.start(); $('startBtn').disabled = true; $('recBtn').disabled = false; $('photoBtn').disabled = false; $('videoBtn').disabled = false;
  } catch (e) { showErr('Could not open the camera: ' + e.message); }
};
$('delBtn').onclick = async () => {
  if (!confirm('Delete all samples for ' + current() + '?')) return;
  await fetch('/api/dataset/' + encodeURIComponent(current()), { method: 'DELETE' }); loadCounts();
};
$('trainBtn').onclick = async () => {
  if (recording) toggleRec();
  $('trainBtn').disabled = true; $('trainMsg').textContent = 'Training… this can take up to a minute.'; $('results').innerHTML = '';
  try {
    const r = await fetch('/api/train', { method: 'POST' }); const d = await r.json();
    if (!r.ok) { showErr(d.error); $('trainMsg').textContent = ''; }
    else {
      showErr('');
      $('trainMsg').textContent = '✅ Done – best model: ' + d.best_model + '. Open the Translator to try it.';
      const rows = Object.entries(d.models).map(([n, m]) =>
        `<tr${n === d.best_model ? ' class="best"' : ''}><td>${n}</td><td>${m.accuracy.toFixed(3)}</td><td>${m.precision.toFixed(3)}</td><td>${m.recall.toFixed(3)}</td><td>${m.f1.toFixed(3)}</td></tr>`).join('');
      $('results').innerHTML = '<table><tr><th>Model</th><th>Accuracy</th><th>Precision</th><th>Recall</th><th>F1</th></tr>' + rows + '</table>';
    }
  } catch (e) { showErr('Training failed: ' + e.message); }
  $('trainBtn').disabled = false;
};
$('photoBtn').onclick = async () => {
  const v = $('video'), c = document.createElement('canvas'); c.width = v.videoWidth; c.height = v.videoHeight;
  const ctx = c.getContext('2d'); ctx.translate(c.width, 0); ctx.scale(-1, 1); ctx.drawImage(v, 0, 0);  // mirrored, like the screen
  const r = await fetch('/api/reference', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image: c.toDataURL('image/jpeg', 0.9), label: current() }) });
  const d = await r.json();
  if (r.ok) { $('refImg').src = d.url; $('signSel').selectedOptions[0].dataset.img = d.url; showErr(''); } else showErr(d.error);
};
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
$('videoBtn').onclick = async () => {
  const type = ['video/webm;codecs=vp9', 'video/webm', 'video/mp4'].find(t => window.MediaRecorder && MediaRecorder.isTypeSupported(t));
  if (!type) { showErr('This browser cannot record video – use Chrome or Edge.'); return; }
  $('videoBtn').disabled = true;
  const v = $('video'), c = document.createElement('canvas'); c.width = v.videoWidth; c.height = v.videoHeight;
  const ctx = c.getContext('2d'); let drawing = true;
  (function draw() { if (!drawing) return; ctx.save(); ctx.translate(c.width, 0); ctx.scale(-1, 1); ctx.drawImage(v, 0, 0); ctx.restore(); requestAnimationFrame(draw); })();
  const rec = new MediaRecorder(c.captureStream(30), { mimeType: type }), chunks = [];
  rec.ondataavailable = (e) => chunks.push(e.data);
  const stopped = new Promise(r => rec.onstop = r);
  for (let i = 3; i > 0; i--) { $('camStatus').textContent = 'Get ready… ' + i; await sleep(1000); }
  $('camStatus').textContent = '● Recording – show the sign'; rec.start(); await sleep(3000); rec.stop(); await stopped; drawing = false;
  const fd = new FormData(); fd.append('label', current()); fd.append('video', new Blob(chunks, { type }), 'demo');
  try {
    const r = await fetch('/api/demo-video', { method: 'POST', body: fd }); const d = await r.json();
    if (r.ok) { const opt = $('signSel').selectedOptions[0]; opt.dataset.video = d.url; refreshSign(); showErr(''); $('camStatus').textContent = 'Demo video saved.'; }
    else showErr(d.error);
  } catch (e) { showErr('Upload failed: ' + e.message); }
  $('videoBtn').disabled = false;
};
fetch('/api/status').then(r => r.json()).then(st => { if (!st.mediapipe_ok) showErr(st.fix); });
loadCounts();
