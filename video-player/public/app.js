// public/app.js
(async function(){
  const VIDEO_EXTENSIONS = ['.mp4','.m4v','.mov','.ts','.webm','.ogg'];
  const videoEl = document.getElementById('video');
  const listEl = document.getElementById('list');
  const metaTitle = document.getElementById('metaTitle');
  const metaInfo = document.getElementById('metaInfo');
  const back5 = document.getElementById('back5');
  const forward5 = document.getElementById('forward5');
  const fsBtn = document.getElementById('fsBtn');
  const speedSelect = document.getElementById('speedSelect');
  const downloadBtn = document.getElementById('downloadBtn');
  const timeLabel = document.getElementById('timeLabel');
  const refreshBtn = document.getElementById('refreshBtn');
  const jumpOverlay = document.getElementById('jumpOverlay');
  const doubleTapLeft = document.getElementById('doubleTapLeft');
  const doubleTapRight = document.getElementById('doubleTapRight');
  const videoWrapper = document.getElementById('videoWrapper');
  const seekBar = document.getElementById('seekBar');
  const seekFill = document.getElementById('seekFill');
  const playerShell = document.getElementById('playerShell');
  const centerPlayBtn = document.getElementById('centerPlayBtn');

  let currentVideo = null;
  let saveInterval = null;
  const SAVE_EVERY_MS = 5000; // every 5 seconds
  const DOUBLE_TAP_WINDOW = 200; // ms
  const CONTROL_HIDE_MS = 2500; // auto-hide seekbar after this when playing
  let isRestoring = false;

  // cookie helpers
  function setCookie(name, value, days=365) {
    try {
      const maxAge = days*24*60*60;
      document.cookie = `${name}=${encodeURIComponent(value)}; Max-Age=${maxAge}; path=/`;
    } catch (e) {
      try { localStorage.setItem(name, value); } catch(e){}
    }
  }
  function getCookie(name) {
    const match = document.cookie.split('; ').find(row => row.startsWith(name + '='));
    if (match) {
      return decodeURIComponent(match.split('=')[1]);
    }
    try { return localStorage.getItem(name); } catch(e){ return null; }
  }

  // format time
  function fmtTime(s) {
    if (isNaN(s) || s === Infinity) return '00:00';
    s = Math.floor(s);
    const hh = Math.floor(s / 3600);
    const mm = Math.floor((s % 3600) / 60);
    const ss = s % 60;
    if (hh) return `${hh}:${String(mm).padStart(2,'0')}:${String(ss).padStart(2,'0')}`;
    return `${String(mm).padStart(2,'0')}:${String(ss).padStart(2,'0')}`;
  }

  function updateTimeLabel() {
    const cur = videoEl.currentTime || 0;
    const dur = videoEl.duration || 0;
    timeLabel.textContent = `${fmtTime(cur)} / ${fmtTime(dur)}`;
    // update seek fill
    if (dur && !isNaN(dur) && dur > 0) {
      const pct = Math.max(0, Math.min(100, (cur/dur)*100));
      seekFill.style.width = pct + '%';
    } else {
      seekFill.style.width = '0%';
    }
  }

  // load video list
  async function loadList(){
    listEl.innerHTML = '<div style="padding:12px;color:var(--muted)">Loading…</div>';
    try {
      const res = await fetch('/api/videos');
      const videos = await res.json();
      renderList(videos);
    } catch (e) {
      listEl.innerHTML = `<div style="padding:12px;color:var(--muted)">Failed to load list</div>`;
    }
  }

  function renderList(videos) {
    if (!videos || !videos.length) {
      listEl.innerHTML = '<div style="padding:12px;color:var(--muted)">No videos in the data/ folder.</div>';
      return;
    }
    listEl.innerHTML = '';
    videos.forEach(v => {
      const card = document.createElement('div');
      card.className = 'video-card';

      const thumb = document.createElement('div');
      thumb.className = 'video-thumb';
      thumb.textContent = '▶';

      // attempt to load a thumbnail (if server created one)
      const img = new Image();
      img.onload = () => {
        thumb.textContent = '';
        thumb.style.background = 'transparent';
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'cover';
        img.style.borderRadius = '6px';
        thumb.appendChild(img);
      };
      img.onerror = ()=> {};
      img.src = `/api/thumbnail/${encodeURIComponent(v.name)}`;

      const meta = document.createElement('div');
      meta.className = 'video-meta';
      const title = document.createElement('div');
      title.className = 'video-title';
      title.textContent = v.name;
      const sub = document.createElement('div');
      sub.className = 'video-sub';
      sub.textContent = `${Math.round(v.size/1024)} KB • ${new Date(v.mtime).toLocaleString()}`;
      meta.appendChild(title);
      meta.appendChild(sub);

      card.appendChild(thumb);
      card.appendChild(meta);
      card.onclick = () => {
        openVideo(v);
      };

      listEl.appendChild(card);
    });
  }

  async function openVideo(v) {
    currentVideo = v;
    metaTitle.textContent = v.name;
    metaInfo.innerHTML = `<div>${Math.round(v.size/1024)} KB</div><div>Uploaded: ${new Date(v.mtime).toLocaleString()}</div>`;

    // show player
    playerShell.classList.remove('hidden');

    // set video source
    const ext = v.name.split('.').pop().toLowerCase();
    while (videoEl.firstChild) videoEl.removeChild(videoEl.firstChild);
    const source = document.createElement('source');
    source.src = v.url;
    if (ext === 'ts') source.type = 'video/mp2t';
    else if (ext === 'webm') source.type = 'video/webm';
    else source.type = 'video/mp4';
    videoEl.appendChild(source);

    // download link
    downloadBtn.href = v.url;
    downloadBtn.setAttribute('download', v.name);

    // attempt poster from thumbnail
    const thumbUrl = `/api/thumbnail/${encodeURIComponent(v.name)}`;
    fetch(thumbUrl, { method: 'HEAD' }).then(r => {
      if (r.ok) {
        videoEl.poster = thumbUrl;
      } else {
        videoEl.removeAttribute('poster');
      }
    }).catch(()=>videoEl.removeAttribute('poster'));

    // stop previous interval
    if (saveInterval) { clearInterval(saveInterval); saveInterval = null; }

    // mark we are restoring so we don't accidentally write "0" to storage while loading
    isRestoring = true;

    // load
    videoEl.load();

    videoEl.onloadedmetadata = () => {
      updateTimeLabel();
      // restore playback speed from cookie/localStorage
      const speed = getCookie('playbackSpeed') || (function(){ try { return localStorage.getItem('playbackSpeed'); } catch(e){ return null; } })();
      if (speed) {
        const sp = parseFloat(speed);
        if (!isNaN(sp)) {
          videoEl.playbackRate = sp;
          speedSelect.value = String(sp);
        }
      }

      // restore progress (cookie first, fallback to localStorage)
      const key = `progress_${encodeURIComponent(v.name)}`;
      let saved = getCookie(key);
      if (!saved) {
        try { saved = localStorage.getItem(key); } catch(e){ saved = null; }
      }
      if (saved) {
        const secs = parseFloat(saved);
        if (!isNaN(secs) && secs >= 0 && secs < videoEl.duration - 0.5) {
          try {
            videoEl.currentTime = secs;
          } catch(e){}
        }
      }

      // give the browser a moment to apply currentTime before allowing saves
      setTimeout(()=> {
        isRestoring = false;
        // start periodic save
        if (saveInterval) clearInterval(saveInterval);
        saveInterval = setInterval(saveProgress, SAVE_EVERY_MS);
        updateTimeLabel();
      }, 150);
    };

    videoEl.ontimeupdate = updateTimeLabel;
    videoEl.onerror = (e) => {
      console.warn('Video error', e);
    };

    // attempt autoplay (but don't require)
    try { await videoEl.play().catch(()=>{}); } catch(e) {}
  }

  function saveProgress() {
    if (!currentVideo || isRestoring) return;
    const secs = videoEl.currentTime || 0;
    const key = `progress_${encodeURIComponent(currentVideo.name)}`;
    // store to one decimal to be slightly more precise than integer
    const toSave = Math.floor(secs * 10) / 10;
    setCookie(key, String(toSave), 365);
    try { localStorage.setItem(key, String(toSave)); } catch(e){}
  }

  // UI control wiring
  back5.onclick = () => { videoEl.currentTime = Math.max(0, (videoEl.currentTime||0) - 5); saveProgress(); showJump(-5); };
  forward5.onclick = () => { videoEl.currentTime = Math.min((videoEl.duration||0), (videoEl.currentTime||0) + 5); saveProgress(); showJump(+5); };

  // center play button toggles playback (visible only when seekBar is visible)
  centerPlayBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    if (videoEl.paused) videoEl.play(); else videoEl.pause();
    // update center button text is handled in onplay/onpause handlers
  });

  speedSelect.onchange = () => {
    const v = parseFloat(speedSelect.value);
    if (!isNaN(v)) {
      videoEl.playbackRate = v;
      setCookie('playbackSpeed', String(v), 365);
      try { localStorage.setItem('playbackSpeed', String(v)); } catch(e){}
    }
  };

  fsBtn.onclick = async () => {
    if (!document.fullscreenElement) {
      try { await videoWrapper.requestFullscreen(); } catch(e){}
    } else {
      try { await document.exitFullscreen(); } catch(e){}
    }
  };

  refreshBtn.onclick = () => loadList();

  // keyboard shortcuts
  document.addEventListener('keydown', (ev) => {
    if (ev.code === 'Space') { ev.preventDefault(); if (videoEl.paused) videoEl.play(); else videoEl.pause(); }
    if (ev.code === 'ArrowLeft') { videoEl.currentTime = Math.max(0, (videoEl.currentTime||0) - 5); showJump(-5); saveProgress(); }
    if (ev.code === 'ArrowRight') { videoEl.currentTime = Math.min((videoEl.duration||0), (videoEl.currentTime||0) + 5); showJump(+5); saveProgress(); }
    if (ev.code === 'KeyF') { if (document.fullscreenElement) document.exitFullscreen(); else videoWrapper.requestFullscreen(); }
  });

  // Seekbar click/tap handling
  function seekAtClientX(clientX) {
    const rect = seekBar.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    if (videoEl.duration && !isNaN(videoEl.duration)) {
      videoEl.currentTime = videoEl.duration * pct;
      saveProgress();
      updateTimeLabel();
    }
  }
  seekBar.addEventListener('click', (e)=> {
    e.stopPropagation(); // don't let the click fall through to the video
    seekAtClientX(e.clientX);
  });
  // support touch
  seekBar.addEventListener('touchstart', (e)=> {
    if (e.touches && e.touches[0]) {
      e.stopPropagation();
      seekAtClientX(e.touches[0].clientX);
    }
  }, {passive:true});

  // auto-hide seekbar logic (controls remain visible)
  let hideTimer = null;
  function showControls() {
    // show the seekbar & center button
    playerShell.classList.add('show-controls');
    document.body.classList.remove('controls-hidden');
    if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
    // auto-hide seekbar when playing
    if (!videoEl.paused) {
      hideTimer = setTimeout(()=> {
        playerShell.classList.remove('show-controls');
        document.body.classList.add('controls-hidden');
      }, CONTROL_HIDE_MS);
    }
  }
  function startHideTimer() { showControls(); }
  function stopHideTimer() { if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; } }

  // show seekbar on pointer movement, touch, focus
  let pointerActivityTimer = null;
  function pointerActivity() {
    showControls();
    if (pointerActivityTimer) clearTimeout(pointerActivityTimer);
    pointerActivityTimer = setTimeout(()=> {
      if (!videoEl.paused) {
        if (hideTimer) clearTimeout(hideTimer);
        hideTimer = setTimeout(()=> {
          playerShell.classList.remove('show-controls');
          document.body.classList.add('controls-hidden');
        }, CONTROL_HIDE_MS);
      }
    }, 250);
  }
  videoWrapper.addEventListener('mousemove', pointerActivity);
  videoWrapper.addEventListener('touchstart', pointerActivity, {passive:true});
  videoWrapper.addEventListener('touchmove', pointerActivity, {passive:true});
  playerShell.addEventListener('mouseenter', pointerActivity);
  playerShell.addEventListener('mouseleave', pointerActivity);

  // single tap vs double-tap handling per side
  const lastTap = { left: 0, right: 0 };
  const tapTimer = { left: null, right: null };
  function handleSingleTapShowControls() {
    // single tap only shows controls (not toggle playback)
    showControls();
  }
  function handleDoubleTap(side) {
    if (side === 'left') {
      videoEl.currentTime = Math.max(0, (videoEl.currentTime||0) - 5);
      showJump(-5, 'left');
    } else {
      videoEl.currentTime = Math.min((videoEl.duration||0), (videoEl.currentTime||0) + 5);
      showJump(+5, 'right');
    }
    saveProgress();
  }

  function onSideTap(side, event) {
    event.preventDefault && event.preventDefault();
    const now = performance.now();
    if (now - lastTap[side] <= DOUBLE_TAP_WINDOW) {
      if (tapTimer[side]) {
        clearTimeout(tapTimer[side]);
        tapTimer[side] = null;
      }
      lastTap[side] = 0;
      handleDoubleTap(side);
    } else {
      lastTap[side] = now;
      tapTimer[side] = setTimeout(()=> {
        tapTimer[side] = null;
        // single tap shows controls only
        handleSingleTapShowControls();
      }, DOUBLE_TAP_WINDOW);
    }
  }

  // Attach handlers for both touch and click
  doubleTapLeft.addEventListener('touchend', (e) => onSideTap('left', e), {passive:false});
  doubleTapRight.addEventListener('touchend', (e) => onSideTap('right', e), {passive:false});
  doubleTapLeft.addEventListener('click', (e) => onSideTap('left', e));
  doubleTapRight.addEventListener('click', (e) => onSideTap('right', e));

  // video click: always just show controls (toggle is via center button now)
  videoEl.addEventListener('click', (e)=> {
    try {
      const rect = seekBar.getBoundingClientRect();
      if (e.clientY >= rect.top && e.clientY <= rect.bottom && e.clientX >= rect.left && e.clientX <= rect.right) {
        // click was on seekbar region; ignore here (seekbar handler will handle it)
        return;
      }
    } catch(e){}
    // always show controls on single click
    handleSingleTapShowControls();
  });

  function showJump(secs, side='') {
    jumpOverlay.textContent = (secs > 0 ? `+${secs}s` : `${secs}s`);
    jumpOverlay.classList.add('show');
    setTimeout(()=> jumpOverlay.classList.remove('show'), 450);
  }

  // periodically save in case user leaves
  window.addEventListener('beforeunload', saveProgress);

  // expose a tiny API for debugging
  window.__player = { openVideo, saveProgress };

  // init playback speed from cookie/localStorage
  (function initSpeed(){
    const s = getCookie('playbackSpeed') || (function(){ try { return localStorage.getItem('playbackSpeed'); } catch(e){ return null; } })();
    if (s) {
      const sp = parseFloat(s);
      if (!isNaN(sp)) {
        speedSelect.value = String(sp);
        videoEl.playbackRate = sp;
      }
    } else {
      // ensure selector reflects true playbackRate (1 by default)
      try { speedSelect.value = String(videoEl.playbackRate || 1); } catch(e){}
    }
  })();

  await loadList();

  // start with seekbar visible
  showControls();

})();

