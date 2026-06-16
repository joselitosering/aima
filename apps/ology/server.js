// Ology — M0 local dev server
// Serves the mockup + program output view for local OBS testing.
const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 8080;
const PUBLIC = path.join(__dirname);

// Permissive headers so OBS's embedded Chromium (CEF) loads cleanly.
app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 'no-store'); // always serve fresh during dev
  next();
});

app.use(express.json({ limit: '64kb' }));
app.use(express.static(PUBLIC, { extensions: ['html'] }));

// Explicit routes (nice-to-have aliases)
app.get('/', (_req, res) => res.sendFile(path.join(PUBLIC, 'index.html')));
app.get('/output', (_req, res) => res.sendFile(path.join(PUBLIC, 'output.html')));

/* ── /sync/latest — cross-device state bridge ──────────────────────────────
   mobile.html POSTs { prog, frame } here on every saveProg() call.
   output.html polls GET /sync/latest every 100ms to receive the latest state.
   This is the only sync path that works across devices (phone → Mac/OBS).
   In-memory only — no disk write, no auth, local network use only.        */
let _syncCache = null;
app.post('/sync/latest', (req, res) => {
  _syncCache = req.body;
  res.json({ ok: true });
});
app.get('/sync/latest', (_req, res) => {
  if (!_syncCache) return res.status(204).end();
  res.json(_syncCache);
});

app.listen(PORT, () => {
  console.log('\n  Ology M0 dev server');
  console.log('  ───────────────────────────────────────────');
  console.log('  Controller (Stage + Mobile): http://localhost:' + PORT + '/');
  console.log('  OBS Program Output view:      http://localhost:' + PORT + '/output.html?ar=16:9&res=1080&fps=30');
  console.log('  ───────────────────────────────────────────');
  console.log('  Stop with Ctrl+C\n');
});
