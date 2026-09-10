#!/bin/bash
set -e
if [ -d "webkit-source" ]; then
  echo "webkit-source already exists, updating..."
  git -C webkit-source fetch --depth 1 origin main || true
else
  echo "Cloning WebKit source (shallow)..."
  git clone --depth 1 https://github.com/WebKit/WebKit webkit-source
fi
echo "WebKit source at webkit-source/ ($(du -sh webkit-source | cut -f1))"
echo "Engine: WebKit (no Gecko, no Blink)"
