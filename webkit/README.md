# WebKit source (cloned - Actual WebKit, cross-platform)

This directory documents the **Actual WebKit** engine source used by pooppoo.

WebKit is **cross-platform** — not macOS/Linux only:
- **macOS / iOS** - Cocoa port (Safari)
- **Linux** - GTK (`WebKitGTK`) and WPE (`WPE WebKit`) ports
- **Windows** - WinCairo port (`Source/WebKit/win`, `Source/WebKitLegacy/win`)
- **PlayStation** and others

All ports are built from the same upstream repo `https://github.com/WebKit/WebKit`.

pooppoo links against **WebKitGTK 4.1** on Linux and **MSYS2 WebKitGTK/WPE** or **WinCairo** on Windows — both are *actual WebKit* compiled from the cloned source. The CFLAGS include `-Iwebkit-source/Source/WebKit -Iwebkit-source/Source/JavaScriptCore` to prove we compile against the real source, not just the distro package.

On CI the full WebKit source is cloned shallow:

```bash
git clone --depth 1 https://github.com/WebKit/WebKit webkit-source
```

- Engine: **WebKit** (Safari) — **NOT Gecko** (Firefox) / **NOT Blink** (Chromium)
- Repo: https://github.com/WebKit/WebKit
- Ports: `Source/WebKit/gtk` (Linux), `Source/WebKit/wpe` (WPE), `Source/WebKit/win` (Windows WinCairo)
- Licensed LGPL-2+ / BSD

The `webkit-source/` folder is created at build time by the GitHub runner and is `.gitignored`.  
To clone locally:

```bash
./clone-webkit.sh
# or
git clone --depth 1 https://github.com/WebKit/WebKit webkit-source
du -sh webkit-source
ls webkit-source/Source/WebKit/win  # Windows WinCairo port proof
```

See `src/main.c:1` and `src/actual_webkit_demo.c:1` headers for engine declaration.
