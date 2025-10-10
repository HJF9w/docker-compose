// server.js
const express = require('express');
const path = require('path');
const fs = require('fs').promises;
const fsSync = require('fs');
const { spawnSync } = require('child_process');
const morgan = require('morgan');

const app = express();
const PORT = process.env.PORT || 3000;

const DATA_DIR = path.join(__dirname, 'data');
const THUMBS_DIR = path.join(__dirname, 'thumbs');

const VIDEO_EXTENSIONS = ['.mp4', '.m4v', '.mov', '.ts', '.webm', '.ogg'];

app.use(morgan('tiny'));
app.use(express.static(path.join(__dirname, 'public')));

// serve raw video files
app.use('/videos', express.static(DATA_DIR, {
  extensions: ['mp4', 'm4v', 'webm', 'ts', 'ogg']
}));

// serve static thumbs if created
if (!fsSync.existsSync(THUMBS_DIR)) {
  try { fsSync.mkdirSync(THUMBS_DIR); } catch (e) {}
}
app.use('/thumbs', express.static(THUMBS_DIR));

// util: check ffmpeg exists
function ffmpegAvailable() {
  try {
    const r = spawnSync('ffmpeg', ['-version'], { stdio: 'ignore' });
    return r.status === 0 || r.status === null;
  } catch (e) {
    return false;
  }
}

const HAS_FFMPEG = ffmpegAvailable();

// list videos
app.get('/api/videos', async (req, res) => {
  try {
    await fs.access(DATA_DIR);
  } catch (e) {
    return res.json([]);
  }

  const files = await fs.readdir(DATA_DIR, { withFileTypes: true });
  const videos = [];

  for (const f of files) {
    if (!f.isFile()) continue;
    const ext = path.extname(f.name).toLowerCase();
    if (!VIDEO_EXTENSIONS.includes(ext)) continue;
    const stat = await fs.stat(path.join(DATA_DIR, f.name));
    videos.push({
      name: f.name,
      url: '/videos/' + encodeURIComponent(f.name),
      size: stat.size,
      mtime: stat.mtimeMs
    });
  }

  // sort by mtime descending (newest first)
  videos.sort((a, b) => b.mtime - a.mtime);

  res.json(videos);
});

// thumbnail endpoint (on-demand generation if ffmpeg present)
app.get('/api/thumbnail/:name', async (req, res) => {
  const raw = req.params.name;
  const name = decodeURIComponent(raw);
  const inputPath = path.join(DATA_DIR, name);

  try {
    await fs.access(inputPath);
  } catch (e) {
    return res.status(404).send('video not found');
  }

  const safeName = name.replace(/[\/\\:?<>|"]/g, '_');
  const outFile = path.join(THUMBS_DIR, safeName + '.jpg');

  // if thumb exists, return it
  if (fsSync.existsSync(outFile)) {
    return res.sendFile(outFile);
  }

  // if ffmpeg not available, 404
  if (!HAS_FFMPEG) {
    return res.status(404).send('thumbnail not available');
  }

  // generate thumbnail (seek to 1s to avoid black frames)
  // note: this spawns ffmpeg synchronously which is simpler here.
  // On heavy traffic, you'd want async and a job queue.
  try {
    // ensure thumbs dir exists
    if (!fsSync.existsSync(THUMBS_DIR)) fsSync.mkdirSync(THUMBS_DIR, { recursive: true });

    // run ffmpeg: -ss 00:00:01 -i input -frames:v 1 -q:v 2 out.jpg
    // for .ts inputs this typically works for basic cases.
    const args = ['-ss', '00:00:01', '-i', inputPath, '-frames:v', '1', '-q:v', '2', outFile, '-y'];
    const spawn = spawnSync('ffmpeg', args, { stdio: 'ignore', timeout: 15000 });

    if (spawn.status !== 0) {
      // generation failed
      if (fsSync.existsSync(outFile)) {
        try { await fs.unlink(outFile); } catch (e) {}
      }
      return res.status(500).send('failed to generate thumbnail');
    }

    return res.sendFile(outFile);
  } catch (err) {
    console.error('thumb-gen error', err);
    return res.status(500).send('thumbnail error');
  }
});

// fallback for SPA (so deep links to player still work)
app.get('*', (req, res, next) => {
  if (req.path.startsWith('/api') || req.path.startsWith('/videos') || req.path.startsWith('/thumbs')) return next();
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`Serving videos from: ${DATA_DIR}`);
  console.log(`Thumbnails enabled: ${HAS_FFMPEG ? 'yes' : 'no'}`);
});

