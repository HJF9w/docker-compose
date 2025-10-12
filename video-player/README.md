# Simple Video Player

Mobile-friendly web app that lists videos from the `data/` directory and plays them with a custom UI:
- YouTube-style double-tap on left/right halves to jump ±5s (200ms double-tap window).
- Playback speed selection (0.25×–3×).
- Saves playback speed and per-video progress in cookies (with localStorage fallback).
- Fullscreen and Picture-in-Picture support, keyboard shortcuts, download button.
- Optional on-demand thumbnail generation when `ffmpeg` is installed (this is enabled in the provided Dockerfile).

## Quick start (local)

1. Place your video files in the `data/` folder (create it if it doesn't exist).
2. Install deps:
```bash
npm install
```
3. Start:
```
npm start
```
4. Open http://localhost:3000 in your browser.

Supported extensions: .mp4, .m4v, .mov, .ts, .webm, .ogg.

Note about .ts files: browsers vary in .ts playback support. If a .ts does not play directly, consider re-muxing to .mp4 (no re-encoding) with ffmpeg:
```
ffmpeg -i input.ts -c copy output.mp4
```
Docker

Build:
```
docker build -t simple-video-player:latest .
```
Run (mount a local data directory):
```
docker run --rm -p 3000:3000 -v /path/to/my/videos:/app/data simple-video-player:latest
```
The image includes ffmpeg so the server can generate thumbnails on demand.

Notes & behavior

Playback speed is stored in cookie playbackSpeed.

Per-video progress is stored in cookies named progress_<encoded-file-name>. Fallback to localStorage is used if cookies are unavailable or exceed limits.

Progress is saved every 5 seconds and on pause/ended/unload.

Double-tap window is 200ms (two taps in under 200ms).

Thumbnail generation uses ffmpeg and seeks to 1 second to capture a frame (if ffmpeg is present). This is done on-demand.
