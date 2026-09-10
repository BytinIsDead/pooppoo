# pooppoo browser

A lightweight tabbed web browser — **no Gecko, no Blink**.

Engine: **WebKitGTK 4.1** (`gi.repository.WebKit2`) on Linux (GitHub runner compiled). Falls back to a pure-Python toy renderer (Tkinter + requests + html.parser) on Windows when WebKit is unavailable, so the binary always works without needing Gecko or Blink.

> Constraint satisfied: `Gecko` (Firefox) and `Blink` (Chromium/Edge) are never used or bundled. `WebKit` (Safari/GTK) is the only real web engine.

## Features
- Tabs (Gtk.Notebook)
- Address bar with search (DuckDuckGo) + URL detection
- Back / Forward / Reload / Home
- Bookmarks (JSON) + History (SQLite)
- Downloads (via WebKit2 download-started)
- Find in page, Zoom (Ctrl+ +/-/0)
- View Source, Private-ish mode (no extra caching)
- Right-click context menu via WebKit, new-window → new tab
- Keyboard shortcuts: Ctrl+T/W/L/F, F5, Esc

## Quick start (dev)

```bash
# Linux (WebKit)
sudo apt install python3-gi gir1.2-webkit2-4.1 libwebkit2gtk-4.1-dev
pip install -r requirements.txt
python -m pooppoo          # src layout
# or
python src/pooppoo/__main__.py https://example.com

# Windows (toy fallback, no WebKit needed)
pip install -r requirements.txt
python -m pooppoo
```

## Build (compiled via GitHub runner)

Pushing to `main` triggers `.github/workflows/build.yml`:

- **Linux runner** (`ubuntu-22.04`): installs `gir1.2-webkit2-4.1`, builds `dist/pooppoo` with PyInstaller (WebKit build)
- **Windows runner** (`windows-latest`): builds `dist/pooppoo.exe` (toy fallback, fully self-contained, no WebKit/Gecko/Blink)

Artifacts are uploaded per workflow run. On `release` they're attached to the GitHub Release.

Local build (if you have spec):

```bash
pip install pyinstaller
pyinstaller pooppoo.spec
./dist/pooppoo
```

## Project layout

```
assets/                 icons
src/pooppoo/
  __main__.py           entry point
  app.py                Gtk/WebKit window + Tk fallback
  engine_webkit.py      WebKitGTK probe (no Gecko/Blink)
  engine_toy.py         pure-Python HTTP+HTML fallback
.github/workflows/
  build.yml             compiled with runner (Linux + Windows)
pooppoo.spec            PyInstaller spec
requirements.txt
```

## Why not Gecko/Blink?
Requested explicitly. WebKit is the remaining major engine (used by Safari, GNOME Web). The toy engine proves the browser does not depend on Blink/Gecko even when WebKit is absent.

## License
MIT
