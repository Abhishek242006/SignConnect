// Practice mode: the real classifier checks whether you perform the requested sign.
const $ = (id) => document.getElementById(id);
let target = null, hits = 0, score = 0, cam = null;

function nextTarget() {
  const s = window.SIGNS[Math.floor(Math.random() * window.SIGNS.length)];
  target = s.word; hits = 0;
  $('target').textContent = s.word; $('result').textContent = '';
  const img = $('targetImg'), vid = $('targetVid');
  vid.hidden = !s.video; img.hidden = !!s.video;
  if (s.video) { vid.src = s.video; vid.play().catch(() => {}); } else { img.src = s.img; img.alt = 'Hand shape for ' + s.word; }
}
function onResult(d) {
  if (d.error) { $('result').textContent = '⚠ ' + d.error; return; }
  $('modelWarn').hidden = d.model_loaded;
  $('seen').textContent = d.word || (d.hand_detected ? 'Unknown' : '—');
  $('conf').textContent = Math.round(d.confidence * 100) + '%';
  hits = d.word === target ? hits + 1 : 0;
  if (hits >= 6) { score++; $('score').textContent = score; $('result').textContent = '✅ Correct! Next sign…'; hits = 0; setTimeout(nextTarget, 1200); }
}
$('startBtn').onclick = async () => {
  cam = cam || new SignCamera($('video'), $('overlay'), onResult);
  try { await cam.start(); $('startBtn').disabled = true; $('skipBtn').disabled = false; nextTarget(); }
  catch (e) { $('result').textContent = 'Could not open the camera: ' + e.message; }
};
$('skipBtn').onclick = nextTarget;
