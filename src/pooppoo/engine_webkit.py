"""
WebKit engine - primary rendering engine for pooppoo browser.
Uses WebKitGTK via PyGObject (gi.repository.WebKit2).
This is NOT Gecko (Firefox) and NOT Blink (Chromium) - satisfies constraint.

On Linux runners WebKit2GTK 4.1 is installed.
On other platforms or if GI unavailable, this module fails gracefully and caller falls back to toy engine.
"""
import sys

try:
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("WebKit2", "4.1")
    from gi.repository import Gtk, WebKit2, GLib, Gdk
    WEBKIT_AVAILABLE = True
except Exception as e:
    WEBKIT_AVAILABLE = False
    _import_error = e
    Gtk = WebKit2 = GLib = Gdk = None


def is_available() -> bool:
    return WEBKIT_AVAILABLE


def get_import_error():
    return _import_error if not WEBKIT_AVAILABLE else None
