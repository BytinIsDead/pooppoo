CC=gcc
# Actual WebKit: prefer WPE (pure WebKit) if available, else WebKitGTK (GTK port of WebKit, still actual WebKit source)
# Both are built from https://github.com/WebKit/WebKit - we clone it in CI
WPE_CFLAGS=$(shell pkg-config --cflags wpe-webkit-1.1 2>/dev/null)
WPE_LIBS=$(shell pkg-config --libs wpe-webkit-1.1 2>/dev/null)
ifeq ($(WPE),1)
  PKG_CFLAGS=$(shell pkg-config --cflags gtk+-3.0 wpe-webkit-1.1) -Iwebkit-source/Source/WebKit -Iwebkit-source/Source/WebCore
  PKG_LIBS=$(shell pkg-config --libs gtk+-3.0 wpe-webkit-1.1) -lsqlite3
else
  PKG_CFLAGS=$(shell pkg-config --cflags gtk+-3.0 webkit2gtk-4.1 2>/dev/null || pkg-config --cflags gtk+-3.0 webkit2gtk-4.0) -Iwebkit-source/Source/WebKit -Iwebkit-source/Source/WebCore
  PKG_LIBS=$(shell pkg-config --libs gtk+-3.0 webkit2gtk-4.1 2>/dev/null || pkg-config --libs gtk+-3.0 webkit2gtk-4.0) -lsqlite3
endif
CFLAGS=-Wall -O2 -std=c11 $(PKG_CFLAGS)
LDFLAGS=$(PKG_LIBS)

SRC=src/main.c
BIN=pooppoo
JSC_SRC=src/actual_webkit_demo.c
JSC_BIN=jsc-demo

all: $(BIN) $(JSC_BIN)

$(BIN): $(SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

$(JSC_BIN): $(JSC_SRC)
	$(CC) -Wall -O2 -std=c11 -Iwebkit-source/Source/JavaScriptCore $(shell pkg-config --cflags javascriptcoregtk-4.1 2>/dev/null || pkg-config --cflags javascriptcoregtk-4.0) -o $@ $^ $(shell pkg-config --libs javascriptcoregtk-4.1 2>/dev/null || pkg-config --libs javascriptcoregtk-4.0) || echo "jsc-demo build skipped (no JSC headers)"

clean:
	rm -f $(BIN) $(JSC_BIN)
	rm -rf build

install: $(BIN)
	install -Dm755 $(BIN) /usr/local/bin/$(BIN)

.PHONY: all clean install
