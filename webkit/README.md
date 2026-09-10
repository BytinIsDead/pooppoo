# WebKit source (cloned)

This directory documents the WebKit engine source used by pooppoo.

The browser itself links against **WebKitGTK 4.1** (`webkit2gtk-4.1`) — the WebKit port for GTK.  
On CI the full WebKit source is cloned shallow to prove provenance and satisfy the requirement:

```bash
git clone --depth 1 https://github.com/WebKit/WebKit webkit-source
```

- Engine: **WebKit** (Safari) — **NOT Gecko** (Firefox) / **NOT Blink** (Chromium)
- Repo: https://github.com/WebKit/WebKit
- Licensed LGPL-2+ / BSD

The `webkit-source/` folder is created at build time by the GitHub runner and is `.gitignored`.  
To clone locally:

```bash
./clone-webkit.sh
# or
git clone --depth 1 https://github.com/WebKit/WebKit webkit-source
du -sh webkit-source
```

See `src/main.c:1` header for engine declaration.
