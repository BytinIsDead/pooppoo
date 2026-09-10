CC=gcc
PKG_CFLAGS=$(shell pkg-config --cflags gtk+-3.0 webkit2gtk-4.1 2>/dev/null || pkg-config --cflags gtk+-3.0 webkit2gtk-4.0)
PKG_LIBS=$(shell pkg-config --libs gtk+-3.0 webkit2gtk-4.1 2>/dev/null || pkg-config --libs gtk+-3.0 webkit2gtk-4.0) -lsqlite3
CFLAGS=-Wall -O2 -std=c11 $(PKG_CFLAGS)
LDFLAGS=$(PKG_LIBS)

SRC=src/main.c
BIN=pooppoo

all: $(BIN)

$(BIN): $(SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

clean:
	rm -f $(BIN)
	rm -rf build

install: $(BIN)
	install -Dm755 $(BIN) /usr/local/bin/$(BIN)

.PHONY: all clean install
