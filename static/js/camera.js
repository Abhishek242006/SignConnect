// Webcam loop: grabs frames, POSTs them to the LOCAL Flask server, draws the hand overlay.
class SignCamera {
  constructor(video, canvas, onResult, maxFps = 8, endpoint = '/api/predict', extra = null) {
    this.endpoint = endpoint; this.extra = extra;
    this.video = video; this.canvas = canvas; this.onResult = onResult;
    this.interval = 1000 / maxFps; this.running = false; this.paused = false;
    this.grab = document.createElement('canvas'); this.grab.width = 320; this.grab.height = 240;
  }
  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
    this.video.srcObject = this.stream;
    await this.video.play();
    this.running = true; this.paused = false; this.loop();
  }
  stop() { this.running = false; if (this.stream) this.stream.getTracks().forEach(t => t.stop()); this.draw(null); }
  setPaused(p) { this.paused = p; if (p) this.draw(null); }
  async loop() {
    while (this.running) {
      const t0 = performance.now();
      if (!this.paused && this.video.readyState >= 2) {
        this.grab.getContext('2d').drawImage(this.video, 0, 0, 320, 240);
        try {
          const body = Object.assign({ image: this.grab.toDataURL('image/jpeg', 0.7) }, this.extra ? this.extra() : {});
          const r = await fetch(this.endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
          const data = await r.json().catch(() => ({}));
          if (!r.ok) { this.draw(null); this.onResult({ error: data.error || ('Server error ' + r.status + ' (see the terminal running app.py)') }); }
          else { this.draw(data.landmarks); this.onResult(data); }
        } catch (e) { this.onResult({ error: 'Cannot reach the local server. Is python app.py running?' }); }
      }
      await new Promise(res => setTimeout(res, Math.max(0, this.interval - (performance.now() - t0))));
    }
  }
  draw(lms) {
    const c = this.canvas, ctx = c.getContext('2d');
    c.width = this.video.videoWidth || 640; c.height = this.video.videoHeight || 480;
    ctx.clearRect(0, 0, c.width, c.height);
    if (!lms || !lms.length) return;
    const P = lms.map(([x, y]) => [x * c.width, y * c.height]);
    const links = [[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[5,9],[9,10],[10,11],[11,12],[9,13],[13,14],[14,15],[15,16],[13,17],[17,18],[18,19],[19,20],[0,17]];
    ctx.lineWidth = 4; ctx.strokeStyle = '#22c55e';
    links.forEach(([a, b]) => { ctx.beginPath(); ctx.moveTo(...P[a]); ctx.lineTo(...P[b]); ctx.stroke(); });
    ctx.fillStyle = '#facc15'; P.forEach(([x, y]) => { ctx.beginPath(); ctx.arc(x, y, 5, 0, 7); ctx.fill(); });
  }
}
