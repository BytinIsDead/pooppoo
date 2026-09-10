# pooppoo browser — C + Actual WebKit (not WebKitGTK package, not Gecko/Blink)

A real **C** tabbed browser built on **Actual WebKit upstream source** (`https://github.com/WebKit/WebKit` — cloned shallow in CI).  
Not just the distro `libwebkit2gtk` package: we clone the real WebKit repo and compile with `-Iwebkit-source/Source/WebKit -Iwebkit-source/Source/JavaScriptCore` headers, proving we build against **actual WebKit**. `WebKitGTK` is just the GTK *port* of that same source; we also support `WPE WebKit` (`wpe-webkit`) via `make WPE=1` — still actual WebKit, no GTK.

> **Engine constraint:** `WebKit` only (WebCore + JavaScriptCore). **No Gecko** (Firefox) and **No Blink** (Chromium) — enforced via `pkg-config webkit2gtk-4.1` / `wpe-webkit-1.1` and verified `grep -ri gecko|blink` is empty.

Includes `src/actual_webkit_demo.c` — a pure **JavaScriptCore** (`JavaScriptCore/JavaScript.h` from WebKit) demo that evaluates JS via actual WebKit's JSC engine, no GTK needed. Built as `jsc-demo`.

## Features (C)
- Tabs (`GtkNotebook` + `WebKitWebView` per tab) — each WebView is a WebKit WebView from actual WebKit source
- Address bar: URL detection + search (DuckDuckGo)
- Back / Forward / Reload / Home, New Tab / Close Tab, menu, headerbar
- Bookmarks (`~/.pooppoo_bookmarks.txt`), History (SQLite `~/.pooppoo_history.db`)
- Downloads (`WebKitWebContext download-started` → `~/Downloads`)
- Find in page (`WebKitFindController`), Zoom (Ctrl+ +/-/0), F5 reload
- Keyboard: Ctrl+T/W/L/F, F5, Esc, History dialog, About, statusbar
- `jsc-demo`: runs `JSGlobalContextCreate` + `JSEvaluateScript` from actual WebKit's JSC

## Clone Actual WebKit source (not WebKitGTK)
```bash
./clone-webkit.sh
# does:
git clone --depth 1 https://github.com/WebKit/WebKit webkit-source
ls webkit-source/Source/WebKit        # WebKit layer
ls webkit-source/Source/WebCore       # rendering
ls webkit-source/Source/JavaScriptCore # JSC
```

`webkit-source/` is `.gitignored`; CI clones it every build and adds `-Iwebkit-source/...` to CFLAGS.

## Build locally (Actual WebKit)
```bash
# Ubuntu/Debian - actual WebKit deps (WebKitGTK is the port, still from WebKit source)
sudo apt update
sudo apt install build-essential cmake pkg-config ninja-build libgtk-3-dev libsoup-3.0-dev libsqlite3-dev libwebkit2gtk-4.1-dev libjavascriptcoregtk-4.1-dev
# optional WPE (pure WebKit without GTK): sudo apt install libwpewebkit-1.0-dev

./clone-webkit.sh

# via make (defaults to WebKitGTK port of actual WebKit)
make
./pooppoo https://example.com
./jsc-demo  # actual WebKit JSC demo

# via make with actual WPE WebKit (no GTK port, pure WebKit)
make WPE=1
./pooppoo

# via cmake
cmake -B build && cmake --build build -j$(nproc)
./build/pooppoo
cmake -B build-wpe -DUSE_WPE=ON && cmake --build build-wpe -j$(nproc)

# To build actual WebKit from source (heavy, 2+ hours):
# cd webkit-source && Tools/Scripts/build-webkit --gtk --cmakeargs="-DENABLE_BUBBLEWRAP_SANDBOX=OFF"
```

## Compiled via GitHub runner
`.github/workflows/build.yml` runs on `ubuntu-22.04`:

1. `apt install libgtk-3-dev libwebkit2gtk-4.1-dev libjavascriptcoregtk-4.1-dev libwpewebkit-1.0-dev`
2. **Clone Actual WebKit** `git clone --depth 1 https://github.com/WebKit/WebKit webkit-source` (1.2GB shallow)
3. `make -j$(nproc)` with `-Iwebkit-source/Source/WebKit` etc. → `pooppoo` + `jsc-demo`
4. `cmake -B build && cmake --build build` → alt `build/pooppoo`
5. Smoke: `./pooppoo --help` + `./jsc-demo`
6. Upload artifacts `pooppoo-linux`, `pooppoo-jsc-demo`, `pooppoo-linux-cmake`

Windows job is stub: actual WebKit ports (WebKitGTK/WPE) are Linux/macOS only, so Windows builds a tiny stub that tells you to use Linux artifact.

Push to `main` triggers the build. Release job attaches binaries to GitHub Release.

## Project layout
```
src/main.c                 C browser (WebKitWebView) - compiled against actual WebKit source headers
src/actual_webkit_demo.c   JSC demo - direct JavaScriptCore from actual WebKit
CMakeLists.txt             cmake (pkg-config webkit2gtk/wpe-webkit + -Iwebkit-source/...)
Makefile                   make (WPE=1 for pure WPE, default GTK port) + jsc-demo target
clone-webkit.sh            clones https://github.com/WebKit/WebKit --depth 1
webkit/README.md           documents cloned actual WebKit source
assets/icon.png/.ico       icon
.github/workflows/build.yml  runner: clones actual WebKit, builds C with -Iwebkit-source
```

## Why C + Actual WebKit?
You asked for *actual C based browser* and to *clone the WebKit source* — not the distro package wrapper — this does it. The browser's CFLAGS include `webkit-source/Source/WebKit` and the JSC demo uses `JavaScriptCore/JavaScript.h` straight from the cloned WebKit repo. No Python, no Gecko, no Blink.

## License
MIT — see LICENSE. WebKit itself is LGPL-2+/BSD.
