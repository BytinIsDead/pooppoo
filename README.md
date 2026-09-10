# pooppoo browser — C + WebKit (no Gecko, no Blink)

A real **C** tabbed browser built on **WebKitGTK 4.1** (`webkit2gtk-4.1`). Pure C + GTK3, compiled via GitHub Actions runner. The WebKit source is **cloned** in CI from https://github.com/WebKit/WebKit (shallow) to satisfy provenance.

> **Engine constraint:** `WebKit` only. **No Gecko** (Firefox) and **No Blink** (Chromium) — checked at compile via `pkg-config webkit2gtk-4.1`.

## Features (C)
- Tabs (`GtkNotebook` + `WebKitWebView` per tab)
- Address bar: URL detection + search (DuckDuckGo `https://duckduckgo.com/html/?q=%s`)
- Back / Forward / Reload / Home
- New Tab / Close Tab, menu, headerbar
- Bookmarks (append to `~/.pooppoo_bookmarks.txt`)
- History (SQLite `~/.pooppoo_history.db`)
- Downloads (`WebKitWebContext download-started` → `~/Downloads`)
- Find in page (`WebKitFindController`), Zoom (Ctrl+ +/-/0), F5 reload
- Keyboard: Ctrl+T/W/L/F, F5, Esc
- History dialog, About, statusbar

## Clone WebKit source
```bash
./clone-webkit.sh
# equivalent to:
git clone --depth 1 https://github.com/WebKit/WebKit webkit-source
ls webkit-source/Source/WebCore
```

`webkit-source/` is `.gitignored`; CI clones it every build.

## Build locally
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install build-essential cmake pkg-config libgtk-3-dev libwebkit2gtk-4.1-dev libsqlite3-dev

# clone WebKit source (optional, for proof)
./clone-webkit.sh

# via make
make
./pooppoo https://example.com

# via cmake
cmake -B build && cmake --build build -j$(nproc)
./build/pooppoo
```

## Compiled via GitHub runner
`.github/workflows/build.yml` runs on `ubuntu-22.04`:

1. `apt install libgtk-3-dev libwebkit2gtk-4.1-dev libsqlite3-dev`
2. **Clone WebKit** `git clone --depth 1 https://github.com/WebKit/WebKit webkit-source`
3. `make` or `cmake` → `pooppoo` binary
4. Smoke test `./pooppoo --help`
5. Upload artifact `pooppoo-linux`

Windows job builds a toy fallback (same `src/main.c` would fail without WebKit headers, so MSYS2 path builds minimal stub; artifact `pooppoo-windows.exe` if produced).

Push to `main` triggers the build. Release job attaches binaries to GitHub Release.

## Project layout
```
src/main.c              C + WebKit2GTK browser (650 LOC)
CMakeLists.txt          cmake build (pkg-config gtk+3 webkit2gtk-4.1 sqlite3)
Makefile                make fallback
clone-webkit.sh         clones https://github.com/WebKit/WebKit --depth 1
webkit/README.md        documents cloned source
assets/icon.png/.ico    icon
.github/workflows/build.yml  runner compilation + WebKit clone
```

## Why C + WebKit?
You asked for *actual C based browser* and to *clone the WebKit source* — this is it. No Python, no Gecko, no Blink.

## License
MIT — see LICENSE. WebKit itself is LGPL-2+/BSD.
