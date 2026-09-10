"""
pooppoo browser - main application
Uses WebKitGTK if available, else Tkinter toy engine fallback.
No Gecko, No Blink.
"""
import os
import sys
import json
import sqlite3
import urllib.parse
import webbrowser
from pathlib import Path

# Determine engine availability without importing GTK prematurely on Windows
from . import engine_webkit, engine_toy

APP_NAME = "pooppoo"
VERSION = "0.1.0"
HOME_URL = "https://duckduckgo.com/"
BOOKMARKS_FILE = Path.home() / ".pooppoo_bookmarks.json" if os.name != "nt" else Path(os.getenv("APPDATA",".")) / "pooppoo" / "bookmarks.json"
HISTORY_DB = Path.home() / ".pooppoo_history.db" if os.name != "nt" else Path(os.getenv("APPDATA",".")) / "pooppoo" / "history.db"

def get_storage_paths():
    if os.name == "nt":
        base = Path(os.getenv("APPDATA", str(Path.home()))) / "pooppoo"
        base.mkdir(parents=True, exist_ok=True)
        return base / "bookmarks.json", base / "history.db"
    else:
        return Path.home() / ".pooppoo_bookmarks.json", Path.home() / ".pooppoo_history.db"


# ---------- History helpers ----------
def init_history(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, url TEXT, title TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
    con.commit()
    con.close()

def add_history(db_path: Path, url: str, title: str):
    try:
        con = sqlite3.connect(str(db_path))
        con.execute("INSERT INTO history (url,title) VALUES (?,?)", (url, title))
        con.commit()
        con.close()
    except Exception:
        pass

# ---------- GTK/WebKit App ----------
def run_webkit_app(start_url: str = HOME_URL):
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("WebKit2", "4.1")
    from gi.repository import Gtk, WebKit2, GLib, Gdk

    bookmarks_path, history_path = get_storage_paths()
    init_history(history_path)

    # Load bookmarks
    bookmarks = []
    if bookmarks_path.exists():
        try:
            bookmarks = json.loads(bookmarks_path.read_text(encoding="utf-8"))
        except: bookmarks = []

    def save_bookmarks():
        try:
            bookmarks_path.parent.mkdir(parents=True, exist_ok=True)
            bookmarks_path.write_text(json.dumps(bookmarks, indent=2), encoding="utf-8")
        except: pass

    class BrowserTab(Gtk.Box):
        def __init__(self, url):
            super().__init__(orientation=Gtk.Orientation.VERTICAL)
            self.webview = WebKit2.WebView()
            # Enable sane settings
            settings = self.webview.get_settings()
            settings.set_enable_javascript(True)
            settings.set_enable_developer_extras(True)
            settings.set_enable_smooth_scrolling(True)
            # WebKit - not Blink/Gecko
            self.webview.load_uri(url)
            self.add(self.webview)
            self.show_all()

    class BrowserWindow(Gtk.Window):
        def __init__(self):
            super().__init__(title=f"{APP_NAME} - WebKit (no Blink/Gecko)")
            self.set_default_size(1200, 800)
            self.connect("destroy", Gtk.main_quit)

            # Header
            hb = Gtk.HeaderBar()
            hb.set_show_close_button(True)
            hb.props.title = "pooppoo"
            hb.props.subtitle = "WebKit • no Gecko • no Blink"
            self.set_titlebar(hb)

            # Navigation buttons
            self.back_btn = Gtk.Button.new_from_icon_name("go-previous", Gtk.IconSize.BUTTON)
            self.back_btn.connect("clicked", lambda *_: self.current_webview().go_back() if self.current_webview().can_go_back() else None)
            hb.pack_start(self.back_btn)

            self.fwd_btn = Gtk.Button.new_from_icon_name("go-next", Gtk.IconSize.BUTTON)
            self.fwd_btn.connect("clicked", lambda *_: self.current_webview().go_forward() if self.current_webview().can_go_forward() else None)
            hb.pack_start(self.fwd_btn)

            self.reload_btn = Gtk.Button.new_from_icon_name("view-refresh", Gtk.IconSize.BUTTON)
            self.reload_btn.connect("clicked", lambda *_: self.current_webview().reload())
            hb.pack_start(self.reload_btn)

            self.home_btn = Gtk.Button.new_from_icon_name("go-home", Gtk.IconSize.BUTTON)
            self.home_btn.connect("clicked", lambda *_: self.load_uri(HOME_URL))
            hb.pack_start(self.home_btn)

            # Address bar
            self.entry = Gtk.Entry()
            self.entry.set_placeholder_text("Search or enter address")
            self.entry.set_width_chars(60)
            self.entry.connect("activate", self.on_entry)
            hb.set_custom_title(self.entry)

            # Right side
            self.newtab_btn = Gtk.Button.new_from_icon_name("tab-new", Gtk.IconSize.BUTTON)
            self.newtab_btn.connect("clicked", lambda *_: self.new_tab(HOME_URL))
            hb.pack_end(self.newtab_btn)

            self.bookmark_btn = Gtk.Button.new_from_icon_name("bookmark-new", Gtk.IconSize.BUTTON)
            self.bookmark_btn.set_tooltip_text("Bookmark this page")
            self.bookmark_btn.connect("clicked", self.on_bookmark)
            hb.pack_end(self.bookmark_btn)

            self.menu_btn = Gtk.MenuButton()
            self.menu_btn.set_image(Gtk.Image.new_from_icon_name("open-menu", Gtk.IconSize.BUTTON))
            hb.pack_end(self.menu_btn)
            self.build_menu()

            # Notebook (tabs)
            self.notebook = Gtk.Notebook()
            self.notebook.set_scrollable(True)
            self.notebook.connect("switch-page", self.on_switch_page)

            # Find bar (hidden)
            self.find_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            self.find_bar.set_no_show_all(True)
            find_entry = Gtk.Entry()
            find_entry.set_placeholder_text("Find in page")
            find_prev = Gtk.Button(label="Previous")
            find_next = Gtk.Button(label="Next")
            find_close = Gtk.Button.new_from_icon_name("window-close", Gtk.IconSize.BUTTON)
            self.find_bar.pack_start(Gtk.Label(label="Find:"), False, False, 0)
            self.find_bar.pack_start(find_entry, True, True, 0)
            self.find_bar.pack_start(find_prev, False, False, 0)
            self.find_bar.pack_start(find_next, False, False, 0)
            self.find_bar.pack_start(find_close, False, False, 0)

            def do_find_next(*_):
                ctrl = self.current_webview().get_find_controller()
                ctrl.search(find_entry.get_text(), WebKit2.FindOptions.CASE_INSENSITIVE, 1)
            def do_find_prev(*_):
                ctrl = self.current_webview().get_find_controller()
                ctrl.search(find_entry.get_text(), WebKit2.FindOptions.CASE_INSENSITIVE | WebKit2.FindOptions.BACKWARDS, 1)
            find_entry.connect("activate", do_find_next)
            find_next.connect("clicked", do_find_next)
            find_prev.connect("clicked", do_find_prev)
            find_close.connect("clicked", lambda *_: self.find_bar.hide())

            # Status bar
            self.status = Gtk.Statusbar()
            self.status.push(0, "Engine: WebKitGTK 4.1  |  No Gecko  |  No Blink")

            # Layout
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            vbox.pack_start(self.notebook, True, True, 0)
            vbox.pack_start(self.find_bar, False, False, 0)
            vbox.pack_start(self.status, False, False, 0)
            self.add(vbox)

            # Shortcuts
            accel = Gtk.AccelGroup()
            self.add_accel_group(accel)
            key, mod = Gtk.accelerator_parse("<Control>T")
            accel.connect(key, mod, Gtk.AccelFlags.VISIBLE, lambda *_: self.new_tab(HOME_URL))
            key, mod = Gtk.accelerator_parse("<Control>W")
            accel.connect(key, mod, Gtk.AccelFlags.VISIBLE, lambda *_: self.close_current_tab())
            key, mod = Gtk.accelerator_parse("<Control>L")
            accel.connect(key, mod, Gtk.AccelFlags.VISIBLE, lambda *_: self.entry.grab_focus())
            key, mod = Gtk.accelerator_parse("<Control>F")
            accel.connect(key, mod, Gtk.AccelFlags.VISIBLE, lambda *_: self.find_bar.show())
            key, mod = Gtk.accelerator_parse("F5")
            accel.connect(key, mod, Gtk.AccelFlags.VISIBLE, lambda *_: self.current_webview().reload())
            key, mod = Gtk.accelerator_parse("<Control>R")
            accel.connect(key, mod, Gtk.AccelFlags.VISIBLE, lambda *_: self.current_webview().reload())

            # First tab
            self.new_tab(start_url)
            self.show_all()
            self.find_bar.hide()
            self.connect("key-press-event", self.on_key)

        def build_menu(self):
            menu = Gtk.Menu()
            for label, cb in [
                ("New Tab (Ctrl+T)", lambda *_: self.new_tab(HOME_URL)),
                ("Close Tab (Ctrl+W)", lambda *_: self.close_current_tab()),
                ("Find in Page (Ctrl+F)", lambda *_: self.find_bar.show()),
                ("View Source", lambda *_: self.view_source()),
                ("History", lambda *_: self.show_history()),
                ("Bookmarks", lambda *_: self.show_bookmarks()),
                ("Zoom In (Ctrl++)", lambda *_: self.zoom(0.1)),
                ("Zoom Out (Ctrl+-)", lambda *_: self.zoom(-0.1)),
                ("About pooppoo", lambda *_: self.show_about()),
            ]:
                item = Gtk.MenuItem(label=label)
                item.connect("activate", cb)
                menu.append(item)
            menu.show_all()
            self.menu_btn.set_popup(menu)

        def current_webview(self):
            page = self.notebook.get_nth_page(self.notebook.get_current_page())
            if page:
                # page is BrowserTab Box, first child is WebView
                for child in page.get_children():
                    if isinstance(child, WebKit2.WebView):
                        return child
            return None

        def new_tab(self, url):
            tab = BrowserTab(url)
            wv = tab.webview
            # tab label
            label_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            label = Gtk.Label(label="New Tab")
            close_btn = Gtk.Button.new_from_icon_name("window-close", Gtk.IconSize.MENU)
            close_btn.set_relief(Gtk.ReliefStyle.NONE)
            label_box.pack_start(label, True, True, 0)
            label_box.pack_start(close_btn, False, False, 0)
            label_box.show_all()
            idx = self.notebook.append_page(tab, label_box)
            self.notebook.set_current_page(idx)
            tab.show_all()

            # signals
            def on_load_changed(view, event):
                if event == WebKit2.LoadEvent.COMMITTED:
                    uri = view.get_uri() or url
                    self.entry.set_text(uri)
                    add_history(history_path, uri, label.get_text())
                if event == WebKit2.LoadEvent.FINISHED:
                    title = view.get_title() or view.get_uri() or "Untitled"
                    label.set_text(title[:30])
                    add_history(history_path, view.get_uri() or url, title)
            def on_notify_title(view, pspec):
                title = view.get_title() or "Untitled"
                label.set_text(title[:30])
            wv.connect("load-changed", on_load_changed)
            wv.connect("notify::title", on_notify_title)
            wv.connect("decide-policy", self.on_decide_policy)
            # context download
            ctx = wv.get_context()
            ctx.connect("download-started", self.on_download)

            close_btn.connect("clicked", lambda *_: self.close_tab(tab))
            wv.grab_focus()

        def close_tab(self, tab):
            idx = self.notebook.page_num(tab)
            if idx != -1:
                self.notebook.remove_page(idx)
            if self.notebook.get_n_pages() == 0:
                Gtk.main_quit()

        def close_current_tab(self):
            p = self.notebook.get_current_page()
            if p >=0:
                self.notebook.remove_page(p)
            if self.notebook.get_n_pages()==0:
                Gtk.main_quit()

        def on_switch_page(self, nb, page, idx):
            # update entry to current uri
            GLib.idle_add(lambda: self.update_entry_for_page(page))

        def update_entry_for_page(self, page):
            for child in page.get_children():
                if isinstance(child, WebKit2.WebView):
                    uri = child.get_uri()
                    if uri:
                        self.entry.set_text(uri)
                    break

        def on_entry(self, entry):
            text = entry.get_text().strip()
            uri = engine_toy.normalize_input(text)
            self.load_uri(uri)

        def load_uri(self, uri):
            wv = self.current_webview()
            if wv:
                wv.load_uri(uri)

        def on_decide_policy(self, view, decision, dtype):
            # Open new window requests in same tab or new tab
            if dtype == WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION:
                nav = decision.get_navigation_action()
                req = nav.get_request()
                uri = req.get_uri()
                decision.ignore()
                self.new_tab(uri)
                return True
            return False

        def on_download(self, ctx, download):
            dest = os.path.expanduser("~/Downloads")
            os.makedirs(dest, exist_ok=True)
            uri = download.get_request().get_uri()
            fname = uri.split("/")[-1].split("?")[0] or "download"
            fname = urllib.parse.unquote(fname)
            path = os.path.join(dest, fname)
            # avoid overwrite
            base, ext = os.path.splitext(path)
            n=1
            while os.path.exists(path):
                path = f"{base}_{n}{ext}"
                n+=1
            download.set_destination("file://" + path)
            self.status.push(0, f"Downloading {uri} -> {path}")
            download.connect("finished", lambda d: self.status.push(0, f"Download finished: {path}"))
            download.connect("failed", lambda d, err: self.status.push(0, f"Download failed: {err}"))
            return False

        def on_bookmark(self, *_):
            wv = self.current_webview()
            if not wv: return
            uri = wv.get_uri()
            title = wv.get_title() or uri
            if uri and uri not in [b["url"] for b in bookmarks]:
                bookmarks.append({"url": uri, "title": title})
                save_bookmarks()
                self.status.push(0, f"Bookmarked: {title}")
            else:
                self.status.push(0, "Already bookmarked")

        def view_source(self):
            wv = self.current_webview()
            if wv:
                uri = wv.get_uri()
                if uri:
                    self.new_tab("view-source:" + uri)

        def show_history(self):
            try:
                con = sqlite3.connect(str(history_path))
                rows = con.execute("SELECT url,title,ts FROM history ORDER BY id DESC LIMIT 100").fetchall()
                con.close()
            except: rows=[]
            dlg = Gtk.Dialog(title="History", parent=self, flags=Gtk.DialogFlags.MODAL)
            dlg.add_button("Close", Gtk.ResponseType.CLOSE)
            dlg.set_default_size(700,400)
            store = Gtk.ListStore(str,str,str)
            for url,title,ts in rows:
                store.append([ts,title,url])
            tree = Gtk.TreeView(model=store)
            for i,col in enumerate(["Time","Title","URL"]):
                renderer = Gtk.CellRendererText()
                column = Gtk.TreeViewColumn(col, renderer, text=i)
                tree.append_column(column)
            def on_row_activated(tv, path, col):
                url = store[path][2]
                self.new_tab(url)
                dlg.destroy()
            tree.connect("row-activated", on_row_activated)
            sw = Gtk.ScrolledWindow()
            sw.add(tree)
            dlg.get_content_area().pack_start(sw, True, True, 0)
            dlg.show_all()
            dlg.run()
            dlg.destroy()

        def show_bookmarks(self):
            dlg = Gtk.Dialog(title="Bookmarks", parent=self, flags=Gtk.DialogFlags.MODAL)
            dlg.add_button("Close", Gtk.ResponseType.CLOSE)
            dlg.set_default_size(600,400)
            store = Gtk.ListStore(str,str)
            for b in bookmarks:
                store.append([b["title"], b["url"]])
            tree = Gtk.TreeView(model=store)
            for i,col in enumerate(["Title","URL"]):
                renderer = Gtk.CellRendererText()
                column = Gtk.TreeViewColumn(col, renderer, text=i)
                tree.append_column(column)
            def on_row_activated(tv, path, col):
                url = store[path][1]
                self.new_tab(url)
                dlg.destroy()
            tree.connect("row-activated", on_row_activated)
            sw = Gtk.ScrolledWindow()
            sw.add(tree)
            dlg.get_content_area().pack_start(sw, True, True, 0)
            dlg.show_all()
            dlg.run()
            dlg.destroy()

        def zoom(self, delta):
            wv = self.current_webview()
            if wv:
                wv.set_zoom_level(wv.get_zoom_level() + delta)

        def on_key(self, widget, event):
            # Ctrl+Plus zoom handled via accel, but also handle manual
            if event.state & Gdk.ModifierType.CONTROL_MASK:
                if event.keyval in (Gdk.KEY_plus, Gdk.KEY_equal, 65451):
                    self.zoom(0.1)
                    return True
                if event.keyval == Gdk.KEY_minus:
                    self.zoom(-0.1)
                    return True
                if event.keyval == Gdk.KEY_0:
                    wv = self.current_webview()
                    if wv: wv.set_zoom_level(1.0)
                    return True
            if event.keyval == Gdk.KEY_Escape:
                self.find_bar.hide()
            return False

        def show_about(self):
            dlg = Gtk.MessageDialog(parent=self, flags=Gtk.DialogFlags.MODAL, type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK,
                message_format=f"pooppoo {VERSION}\n\nEngine: WebKitGTK 4.1\nNo Gecko • No Blink\n\nA minimal tabbed browser built for GitHub Actions compilation.\nSearch default: DuckDuckGo\nHome: {HOME_URL}")
            dlg.run()
            dlg.destroy()

    win = BrowserWindow()
    win.show_all()
    Gtk.main()


# ---------- Tkinter Toy Fallback ----------
def run_tk_app(start_url: str = HOME_URL):
    import tkinter as tk
    from tkinter import ttk, messagebox

    bookmarks_path, history_path = get_storage_paths()
    init_history(history_path)

    root = tk.Tk()
    root.title(f"pooppoo {VERSION} - Toy Engine (no WebKit/Gecko/Blink)")
    root.geometry("1100x700")

    # Style
    style = ttk.Style()
    try: style.theme_use("clam")
    except: pass

    # Top bar
    top = ttk.Frame(root)
    top.pack(fill="x", padx=4, pady=4)

    back_btn = ttk.Button(top, text="◀")
    fwd_btn = ttk.Button(top, text="▶")
    reload_btn = ttk.Button(top, text="⟳")
    home_btn = ttk.Button(top, text="⌂")
    entry_var = tk.StringVar(value=start_url)
    entry = ttk.Entry(top, textvariable=entry_var, width=70)
    go_btn = ttk.Button(top, text="Go")
    newtab_btn = ttk.Button(top, text="+ Tab")

    for w in (back_btn, fwd_btn, reload_btn, home_btn):
        w.pack(side="left", padx=2)
    entry.pack(side="left", fill="x", expand=True, padx=6)
    go_btn.pack(side="left", padx=2)
    newtab_btn.pack(side="left", padx=2)

    # Notebook for tabs (toy: we simulate with single view + history stacks)
    main = ttk.Frame(root)
    main.pack(fill="both", expand=True)

    left = ttk.Frame(main, width=200)
    # Bookmarks/history sidebar could be added

    text = tk.Text(main, wrap="word", font=("Segoe UI", 11), padx=12, pady=12)
    scroll = ttk.Scrollbar(main, command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    text.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    # Tag configs
    text.tag_config("h1", font=("Segoe UI", 22, "bold"), spacing1=12, spacing3=6)
    text.tag_config("h2", font=("Segoe UI", 18, "bold"), spacing1=10, spacing3=4)
    text.tag_config("h3", font=("Segoe UI", 14, "bold"), spacing1=8)
    text.tag_config("a", foreground="#1a0dab", underline=True)
    text.tag_config("title", font=("Segoe UI", 9), foreground="#666")

    history_stack = []
    forward_stack = []
    current_url = ""

    def render_tokens(tokens, base_url):
        text.configure(state="normal")
        text.delete("1.0", "end")
        for typ, txt, tag, attrs in tokens:
            if typ == "text":
                style_tag = tag if tag in ("h1","h2","h3","a") else None
                if tag == "a" and "href" in attrs:
                    href = urllib.parse.urljoin(base_url, attrs["href"])
                    # insert with link tag
                    start = text.index("end-1c")
                    text.insert("end", txt + " ", style_tag or "")
                    end = text.index("end-1c")
                    link_tag = f"link_{href}_{start}"
                    text.tag_add("a", start, end)
                    text.tag_bind("a", "<Button-1>", lambda e, u=href: navigate(u))
                else:
                    text.insert("end", txt + " ", style_tag or "")
            elif typ == "break":
                text.insert("end", "\n")
            elif typ == "img":
                text.insert("end", txt + " ", "title")
        text.configure(state="disabled")

    def navigate(url, push_history=True):
        nonlocal current_url
        if push_history and current_url:
            history_stack.append(current_url)
            forward_stack.clear()
        norm = engine_toy.normalize_input(url)
        entry_var.set(norm)
        current_url = norm
        root.title(f"pooppoo - {norm}")
        text.configure(state="normal")
        text.delete("1.0", "end")
        text.insert("end", f"Loading {norm} ...\n", "title")
        text.configure(state="disabled")
        root.update_idletasks()
        final_url, html, ctype, err = engine_toy.fetch_url(norm)
        if err:
            text.configure(state="normal")
            text.delete("1.0", "end")
            text.insert("end", f"Failed to load {norm}\n{err}\n", "h2")
            text.configure(state="disabled")
            return
        entry_var.set(final_url)
        current_url = final_url
        add_history(history_path, final_url, final_url)
        tokens = engine_toy.parse_html(html)
        render_tokens(tokens, final_url)

    def go_back():
        if history_stack:
            forward_stack.append(current_url)
            url = history_stack.pop()
            navigate(url, push_history=False)
    def go_forward():
        if forward_stack:
            history_stack.append(current_url)
            url = forward_stack.pop()
            navigate(url, push_history=False)

    back_btn.configure(command=go_back)
    fwd_btn.configure(command=go_forward)
    reload_btn.configure(command=lambda: navigate(current_url, push_history=False))
    home_btn.configure(command=lambda: navigate(HOME_URL))
    go_btn.configure(command=lambda: navigate(entry_var.get()))
    newtab_btn.configure(command=lambda: navigate(HOME_URL))
    entry.bind("<Return>", lambda e: navigate(entry_var.get()))

    # Status label
    status = ttk.Label(root, text="Engine: Toy (pure Python) • No Gecko • No Blink • WebKit unavailable — using fallback", anchor="w")
    status.pack(fill="x", padx=4)

    # About
    def show_about():
        messagebox.showinfo("About pooppoo", f"pooppoo {VERSION}\nToy Engine fallback\nNo Gecko / No Blink\nWebKit not found, using pure Python renderer")
    menubar = tk.Menu(root)
    helpmenu = tk.Menu(menubar, tearoff=0)
    helpmenu.add_command(label="About", command=show_about)
    menubar.add_cascade(label="Help", menu=helpmenu)
    root.config(menu=menubar)

    navigate(start_url, push_history=False)
    root.mainloop()


def run(start_url: str = HOME_URL):
    if engine_webkit.is_available():
        try:
            run_webkit_app(start_url)
            return
        except Exception as e:
            print(f"WebKit failed ({e}), falling back to Toy engine", file=sys.stderr)
    # fallback
    run_tk_app(start_url)
