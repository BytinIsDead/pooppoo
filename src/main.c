/* pooppoo browser - C + WebKitGTK (no Gecko, no Blink)
 * Clone of WebKit source is done in CI: git clone https://github.com/WebKit/WebKit
 * Engine: WebKit2GTK 4.1 (Safari's engine) - NOT Gecko (Firefox) NOT Blink (Chromium)
 * Build: cmake / make with pkg-config gtk+-3.0 webkit2gtk-4.1 sqlite3
 */
#include <gtk/gtk.h>
#include <webkit2/webkit2.h>
#include <sqlite3.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

#define APP_NAME "pooppoo"
#define VERSION "0.2.0-c"
#define HOME_URL "https://duckduckgo.com/"
#define SEARCH_FMT "https://duckduckgo.com/html/?q=%s"
#define BOOKMARKS_PATH ".pooppoo_bookmarks.txt"
#define HISTORY_DB ".pooppoo_history.db"

static GtkNotebook *notebook;
static GtkEntry *url_entry;
static GtkStatusbar *statusbar;
static GtkWindow *main_window;
static sqlite3 *history_db = NULL;

// ---------- utils ----------
static gboolean is_probable_url(const char *s) {
    if (!s || !*s) return FALSE;
    if (g_str_has_prefix(s, "http://") || g_str_has_prefix(s, "https://")) return TRUE;
    // contains space -> search, else if contains dot and no spaces -> url
    if (strchr(s, ' ') && !strchr(s, '.')) return FALSE;
    if (strchr(s, '.') && !strchr(s, ' ') && strlen(s) > 3) return TRUE;
    if (g_strcmp0(s,"localhost")==0) return TRUE;
    return FALSE;
}

static char* normalize_input(const char *input) {
    if (!input || !*input) return g_strdup(HOME_URL);
    char *trim = g_strstrip(g_strdup(input));
    if (!*trim) { g_free(trim); return g_strdup(HOME_URL); }
    char *res;
    if (is_probable_url(trim)) {
        if (g_str_has_prefix(trim, "http://") || g_str_has_prefix(trim, "https://"))
            res = g_strdup(trim);
        else
            res = g_strdup_printf("https://%s", trim);
    } else {
        char *enc = soup_uri_encode(trim, NULL); // use glib uri escape instead
        // glib fallback
        if (!enc) enc = g_uri_escape_string(trim, NULL, FALSE);
        else {
            // soup_uri_encode not available without libsoup, use g_uri_escape
            g_free(enc);
            enc = g_uri_escape_string(trim, NULL, FALSE);
        }
        res = g_strdup_printf(SEARCH_FMT, enc);
        g_free(enc);
    }
    g_free(trim);
    return res;
}

static void init_history_db(void) {
    char *path = g_build_filename(g_get_home_dir(), HISTORY_DB, NULL);
    if (sqlite3_open(path, &history_db) == SQLITE_OK) {
        const char *sql = "CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, url TEXT, title TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP);";
        sqlite3_exec(history_db, sql, 0,0,0);
    }
    g_free(path);
}
static void add_history(const char *url, const char *title) {
    if (!history_db || !url) return;
    sqlite3_stmt *stmt;
    const char *sql = "INSERT INTO history(url,title) VALUES(?,?)";
    if (sqlite3_prepare_v2(history_db, sql, -1, &stmt, NULL)==SQLITE_OK) {
        sqlite3_bind_text(stmt,1,url,-1,SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt,2,title?title:url,-1,SQLITE_TRANSIENT);
        sqlite3_step(stmt);
        sqlite3_finalize(stmt);
    }
}

// ---------- tab helpers ----------
static WebKitWebView* current_webview(void) {
    int p = gtk_notebook_get_current_page(notebook);
    if (p < 0) return NULL;
    GtkWidget *page = gtk_notebook_get_nth_page(notebook, p);
    if (!page) return NULL;
    // page is GtkBox containing WebView as first expand child
    GList *children = gtk_container_get_children(GTK_CONTAINER(page));
    WebKitWebView *v = NULL;
    for (GList *l=children;l;l=l->next) {
        if (WEBKIT_IS_WEB_VIEW(l->data)) { v = WEBKIT_WEB_VIEW(l->data); break; }
    }
    g_list_free(children);
    return v;
}

static void update_url_entry(WebKitWebView *view) {
    if (!view) return;
    const char *uri = webkit_web_view_get_uri(view);
    if (uri) gtk_entry_set_text(url_entry, uri);
}

static void on_load_changed(WebKitWebView *view, WebKitLoadEvent event, gpointer user_data) {
    GtkLabel *tab_label = GTK_LABEL(user_data);
    if (event == WEBKIT_LOAD_COMMITTED) {
        const char *uri = webkit_web_view_get_uri(view);
        if (uri) {
            gtk_entry_set_text(url_entry, uri);
            add_history(uri, gtk_label_get_text(tab_label));
            gtk_statusbar_push(statusbar, 0, uri);
        }
    } else if (event == WEBKIT_LOAD_FINISHED) {
        const char *title = webkit_web_view_get_title(view);
        const char *uri = webkit_web_view_get_uri(view);
        if (title) gtk_label_set_text(tab_label, title);
        if (uri) add_history(uri, title ? title : uri);
        // update entry if this is current tab
        if (view == current_webview()) update_url_entry(view);
    }
}
static void on_notify_title(GObject *obj, GParamSpec *pspec, gpointer user_data) {
    WebKitWebView *view = WEBKIT_WEB_VIEW(obj);
    GtkLabel *label = GTK_LABEL(user_data);
    const char *title = webkit_web_view_get_title(view);
    if (title && *title) {
        char buf[64];
        g_strlcpy(buf, title, sizeof(buf));
        gtk_label_set_text(label, buf);
        gtk_label_set_ellipsize(label, PANGO_ELLIPSIZE_END);
        gtk_label_set_max_width_chars(label, 28);
    }
}
static gboolean on_decide_policy(WebKitWebView *view, WebKitPolicyDecision *decision, WebKitPolicyDecisionType type, gpointer _unused) {
    if (type == WEBKIT_POLICY_DECISION_TYPE_NEW_WINDOW_ACTION) {
        WebKitNavigationAction *nav = webkit_navigation_policy_decision_get_navigation_action(WEBKIT_NAVIGATION_POLICY_DECISION(decision));
        WebKitURIRequest *req = webkit_navigation_action_get_request(nav);
        const char *uri = webkit_uri_request_get_uri(req);
        if (uri) {
            // open in new tab
            webkit_policy_decision_ignore(decision);
            // forward to new tab creator
            extern void new_tab(const char *url);
            new_tab(uri);
            return TRUE;
        }
    }
    return FALSE;
}
static gboolean on_download_started(WebKitWebContext *ctx, WebKitDownload *dl, gpointer _u) {
    const char *uri = webkit_uri_request_get_uri(webkit_download_get_request(dl));
    const char *dest_dir = g_get_user_special_dir(G_USER_DIRECTORY_DOWNLOAD);
    if (!dest_dir) dest_dir = g_get_home_dir();
    // filename from uri
    const char *slash = strrchr(uri, '/');
    const char *fname = slash ? slash+1 : "download";
    char *q = strchr(fname, '?'); if (q) * (char*)q = '\0';
    char *path = g_build_filename(dest_dir, fname && *fname ? fname : "download", NULL);
    // avoid overwrite
    if (g_file_test(path, G_FILE_TEST_EXISTS)) {
        char *base = g_strdup(path);
        char *dot = strrchr(base, '.');
        int n=1;
        char *npath;
        do {
            if (dot) {
                *dot='\0';
                npath = g_strdup_printf("%s_%d%s", base, n, dot+1);
                // reconstruct
                char *tmp = g_strdup_printf("%s_%d.%s", base, n, dot+1);
                g_free(npath); npath=tmp;
            } else {
                npath = g_strdup_printf("%s_%d", base, n);
            }
            g_free(path); path=npath; n++;
        } while(g_file_test(path, G_FILE_TEST_EXISTS) && n<100);
        g_free(base);
    }
    char *file_uri = g_filename_to_uri(path, NULL, NULL);
    webkit_download_set_destination(dl, file_uri);
    char *msg = g_strdup_printf("Downloading %s -> %s", uri, path);
    gtk_statusbar_push(statusbar,0,msg);
    g_free(msg); g_free(file_uri); g_free(path);
    g_signal_connect(dl, "finished", G_CALLBACK(+[](WebKitDownload *d, gpointer u){
        char *p = g_filename_from_uri(webkit_download_get_destination(d),NULL,NULL);
        char *m = g_strdup_printf("Finished: %s", p? p: webkit_download_get_destination(d));
        gtk_statusbar_push(statusbar,0,m);
        g_free(m); g_free(p);
    }), NULL);
    return FALSE;
}

static void close_tab_widget(GtkWidget *page) {
    int idx = gtk_notebook_page_num(notebook, page);
    if (idx >=0) gtk_notebook_remove_page(notebook, idx);
    if (gtk_notebook_get_n_pages(notebook)==0) gtk_main_quit();
}

void new_tab(const char *url) {
    if (!url) url = HOME_URL;
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    WebKitWebView *view = WEBKIT_WEB_VIEW(webkit_web_view_new());
    WebKitSettings *s = webkit_web_view_get_settings(view);
    g_object_set(s, "enable-javascript", TRUE, "enable-developer-extras", TRUE, "enable-smooth-scrolling", TRUE, NULL);

    // tab label
    GtkWidget *hbox = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 4);
    GtkWidget *label = gtk_label_new("New Tab");
    gtk_label_set_max_width_chars(GTK_LABEL(label), 28);
    gtk_label_set_ellipsize(GTK_LABEL(label), PANGO_ELLIPSIZE_END);
    GtkWidget *close = gtk_button_new_from_icon_name("window-close", GTK_ICON_SIZE_MENU);
    gtk_button_set_relief(GTK_BUTTON(close), GTK_RELIEF_NONE);
    gtk_widget_set_focus_on_click(close, FALSE);
    gtk_box_pack_start(GTK_BOX(hbox), label, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(hbox), close, FALSE, FALSE, 0);
    gtk_widget_show_all(hbox);

    gtk_box_pack_start(GTK_BOX(box), GTK_WIDGET(view), TRUE, TRUE, 0);
    gtk_widget_show_all(box);

    int idx = gtk_notebook_append_page(notebook, box, hbox);
    gtk_notebook_set_tab_reorderable(notebook, box, TRUE);
    gtk_notebook_set_current_page(notebook, idx);

    g_signal_connect(view, "load-changed", G_CALLBACK(on_load_changed), label);
    g_signal_connect(view, "notify::title", G_CALLBACK(on_notify_title), label);
    g_signal_connect(view, "decide-policy", G_CALLBACK(on_decide_policy), NULL);
    WebKitWebContext *ctx = webkit_web_view_get_context(view);
    g_signal_connect(ctx, "download-started", G_CALLBACK(on_download_started), NULL);

    g_signal_connect(close, "clicked", G_CALLBACK(+[](GtkButton *b, gpointer p){
        close_tab_widget(GTK_WIDGET(p));
    }), box);

    webkit_web_view_load_uri(view, url);
    gtk_widget_grab_focus(GTK_WIDGET(view));
    // update entry
    gtk_entry_set_text(url_entry, url);
}

// ---------- callbacks ----------
static void on_entry_activate(GtkEntry *e, gpointer _) {
    const char *txt = gtk_entry_get_text(e);
    char *url = normalize_input(txt);
    WebKitWebView *v = current_webview();
    if (v) webkit_web_view_load_uri(v, url);
    else new_tab(url);
    g_free(url);
}
static void on_back(GtkButton *b, gpointer _) {
    WebKitWebView *v = current_webview(); if (v && webkit_web_view_can_go_back(v)) webkit_web_view_go_back(v);
}
static void on_forward(GtkButton *b, gpointer _) {
    WebKitWebView *v = current_webview(); if (v && webkit_web_view_can_go_forward(v)) webkit_web_view_go_forward(v);
}
static void on_reload(GtkButton *b, gpointer _) {
    WebKitWebView *v = current_webview(); if (v) webkit_web_view_reload(v);
}
static void on_home(GtkButton *b, gpointer _) {
    WebKitWebView *v = current_webview(); if (v) webkit_web_view_load_uri(v, HOME_URL); else new_tab(HOME_URL);
}
static void on_newtab(GtkButton *b, gpointer _) { new_tab(HOME_URL); }
static void on_close_tab(GtkButton *b, gpointer _) {
    int p = gtk_notebook_get_current_page(notebook);
    if (p>=0) { GtkWidget *page = gtk_notebook_get_nth_page(notebook,p); close_tab_widget(page); }
}
static void on_zoom_in(GtkButton *b, gpointer _) {
    WebKitWebView *v = current_webview(); if(v) webkit_web_view_set_zoom_level(v, webkit_web_view_get_zoom_level(v)+0.1);
}
static void on_zoom_out(GtkButton *b, gpointer _) {
    WebKitWebView *v = current_webview(); if(v) webkit_web_view_set_zoom_level(v, webkit_web_view_get_zoom_level(v)-0.1);
}
static void on_bookmark(GtkButton *b, gpointer _) {
    WebKitWebView *v = current_webview(); if(!v) return;
    const char *uri = webkit_web_view_get_uri(v);
    const char *title = webkit_web_view_get_title(v);
    if (!uri) return;
    char *path = g_build_filename(g_get_home_dir(), BOOKMARKS_PATH, NULL);
    FILE *f = fopen(path, "a");
    if (f) { fprintf(f, "%s | %s\n", title?title:"", uri); fclose(f); }
    char *msg = g_strdup_printf("Bookmarked: %s", title?title:uri);
    gtk_statusbar_push(statusbar,0,msg);
    g_free(msg); g_free(path);
}
static void show_history_dialog(void) {
    GtkWidget *dlg = gtk_dialog_new_with_buttons("History", main_window, GTK_DIALOG_MODAL, "_Close", GTK_RESPONSE_CLOSE, NULL);
    gtk_window_set_default_size(GTK_WINDOW(dlg), 700, 400);
    GtkWidget *sw = gtk_scrolled_window_new(NULL,NULL);
    GtkListStore *store = gtk_list_store_new(3, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    if (history_db) {
        sqlite3_stmt *stmt;
        if (sqlite3_prepare_v2(history_db, "SELECT url,title,ts FROM history ORDER BY id DESC LIMIT 100", -1, &stmt, NULL)==SQLITE_OK) {
            while(sqlite3_step(stmt)==SQLITE_ROW) {
                const char *url = (const char*)sqlite3_column_text(stmt,0);
                const char *title = (const char*)sqlite3_column_text(stmt,1);
                const char *ts = (const char*)sqlite3_column_text(stmt,2);
                GtkTreeIter iter; gtk_list_store_append(store,&iter);
                gtk_list_store_set(store,&iter,0,ts?ts:"",1,title?title:"",2,url?url:"",-1);
            }
            sqlite3_finalize(stmt);
        }
    }
    GtkWidget *tree = gtk_tree_view_new_with_model(GTK_TREE_MODEL(store));
    const char *cols[]={"Time","Title","URL"};
    for(int i=0;i<3;i++){
        GtkCellRenderer *r = gtk_cell_renderer_text_new();
        GtkTreeViewColumn *c = gtk_tree_view_column_new_with_attributes(cols[i], r, "text", i, NULL);
        gtk_tree_view_append_column(GTK_TREE_VIEW(tree), c);
    }
    g_signal_connect(tree, "row-activated", G_CALLBACK(+[](GtkTreeView *tv, GtkTreePath *path, GtkTreeViewColumn *col, gpointer dlg){
        GtkTreeModel *m = gtk_tree_view_get_model(tv);
        GtkTreeIter iter; gtk_tree_model_get_iter(m,&iter,path);
        char *url; gtk_tree_model_get(m,&iter,2,&url,-1);
        if(url){ new_tab(url); gtk_widget_destroy(GTK_WIDGET(dlg)); g_free(url); }
    }), dlg);
    gtk_container_add(GTK_CONTAINER(sw), tree);
    GtkWidget *content = gtk_dialog_get_content_area(GTK_DIALOG(dlg));
    gtk_box_pack_start(GTK_BOX(content), sw, TRUE, TRUE, 0);
    gtk_widget_show_all(dlg);
    gtk_dialog_run(GTK_DIALOG(dlg));
    gtk_widget_destroy(dlg);
}
static void show_about(void) {
    GtkWidget *dlg = gtk_message_dialog_new(main_window, GTK_DIALOG_MODAL, GTK_MESSAGE_INFO, GTK_BUTTONS_OK,
        "%s %s\n\nEngine: WebKitGTK 4.1\nNo Gecko • No Blink\n\nWebKit source cloned from https://github.com/WebKit/WebKit\nBuilt with runner (GitHub Actions)\nHome: %s", APP_NAME, VERSION, HOME_URL);
    gtk_dialog_run(GTK_DIALOG(dlg)); gtk_widget_destroy(dlg);
}
static gboolean on_key_press(GtkWidget *w, GdkEventKey *ev, gpointer _) {
    if (ev->state & GDK_CONTROL_MASK) {
        if (ev->keyval == GDK_KEY_t || ev->keyval == GDK_KEY_T) { new_tab(HOME_URL); return TRUE; }
        if (ev->keyval == GDK_KEY_w || ev->keyval == GDK_KEY_W) { on_close_tab(NULL,NULL); return TRUE; }
        if (ev->keyval == GDK_KEY_l || ev->keyval == GDK_KEY_L) { gtk_widget_grab_focus(GTK_WIDGET(url_entry)); return TRUE; }
        if (ev->keyval == GDK_KEY_plus || ev->keyval == GDK_KEY_equal) { on_zoom_in(NULL,NULL); return TRUE; }
        if (ev->keyval == GDK_KEY_minus) { on_zoom_out(NULL,NULL); return TRUE; }
        if (ev->keyval == GDK_KEY_0) { WebKitWebView *v=current_webview(); if(v) webkit_web_view_set_zoom_level(v,1.0); return TRUE; }
        if (ev->keyval == GDK_KEY_f || ev->keyval == GDK_KEY_F) {
            // find: use webkit find controller prompt
            GtkWidget *d = gtk_dialog_new_with_buttons("Find", main_window, GTK_DIALOG_MODAL, "_Find", GTK_RESPONSE_OK, "_Close", GTK_RESPONSE_CLOSE, NULL);
            GtkWidget *e = gtk_entry_new(); gtk_entry_set_placeholder_text(GTK_ENTRY(e), "Find in page");
            gtk_box_pack_start(GTK_BOX(gtk_dialog_get_content_area(GTK_DIALOG(d))), e, TRUE, TRUE, 6);
            gtk_widget_show_all(d);
            if (gtk_dialog_run(GTK_DIALOG(d))==GTK_RESPONSE_OK) {
                const char *txt = gtk_entry_get_text(GTK_ENTRY(e));
                WebKitWebView *v=current_webview();
                if (v && txt && *txt) {
                    WebKitFindController *fc = webkit_web_view_get_find_controller(v);
                    webkit_find_controller_search(fc, txt, WEBKIT_FIND_OPTIONS_CASE_INSENSITIVE, 100);
                }
            }
            gtk_widget_destroy(d); return TRUE;
        }
    }
    if (ev->keyval == GDK_KEY_F5) { on_reload(NULL,NULL); return TRUE; }
    return FALSE;
}
static void on_switch_page(GtkNotebook *nb, GtkWidget *page, guint idx, gpointer _) {
    // update url entry
    GtkWidget *box = gtk_notebook_get_nth_page(nb, idx);
    if (!box) return;
    GList *children = gtk_container_get_children(GTK_CONTAINER(box));
    for(GList *l=children;l;l=l->next) if (WEBKIT_IS_WEB_VIEW(l->data)) { update_url_entry(WEBKIT_WEB_VIEW(l->data)); break; }
    g_list_free(children);
}

int main(int argc, char *argv[]) {
    gtk_init(&argc, &argv);
    init_history_db();

    const char *start = (argc>1 && argv[1][0]!='-') ? argv[1] : HOME_URL;
    if (argc>1 && (g_strcmp0(argv[1],"--help")==0 || g_strcmp0(argv[1],"-h")==0)) {
        g_print("pooppoo %s - C + WebKitGTK (no Gecko/Blink)\nUsage: pooppoo [url]\nWebKit source: https://github.com/WebKit/WebKit\n", VERSION);
        return 0;
    }

    main_window = GTK_WINDOW(gtk_window_new(GTK_WINDOW_TOPLEVEL));
    gtk_window_set_title(main_window, APP_NAME " - WebKit (no Gecko/Blink) " VERSION);
    gtk_window_set_default_size(main_window, 1200, 800);
    g_signal_connect(main_window, "destroy", G_CALLBACK(gtk_main_quit), NULL);
    g_signal_connect(main_window, "key-press-event", G_CALLBACK(on_key_press), NULL);

    // HeaderBar
    GtkHeaderBar *hb = GTK_HEADER_BAR(gtk_header_bar_new());
    gtk_header_bar_set_show_close_button(hb, TRUE);
    gtk_header_bar_set_title(hb, "pooppoo");
    gtk_header_bar_set_subtitle(hb, "WebKit • C • no Gecko • no Blink");
    gtk_window_set_titlebar(main_window, GTK_WIDGET(hb));

    GtkWidget *back = gtk_button_new_from_icon_name("go-previous", GTK_ICON_SIZE_BUTTON);
    GtkWidget *fwd = gtk_button_new_from_icon_name("go-next", GTK_ICON_SIZE_BUTTON);
    GtkWidget *reload = gtk_button_new_from_icon_name("view-refresh", GTK_ICON_SIZE_BUTTON);
    GtkWidget *home = gtk_button_new_from_icon_name("go-home", GTK_ICON_SIZE_BUTTON);
    g_signal_connect(back,"clicked",G_CALLBACK(on_back),NULL);
    g_signal_connect(fwd,"clicked",G_CALLBACK(on_forward),NULL);
    g_signal_connect(reload,"clicked",G_CALLBACK(on_reload),NULL);
    g_signal_connect(home,"clicked",G_CALLBACK(on_home),NULL);
    gtk_header_bar_pack_start(hb, back);
    gtk_header_bar_pack_start(hb, fwd);
    gtk_header_bar_pack_start(hb, reload);
    gtk_header_bar_pack_start(hb, home);

    url_entry = GTK_ENTRY(gtk_entry_new());
    gtk_entry_set_placeholder_text(url_entry, "Search or enter address");
    gtk_widget_set_size_request(GTK_WIDGET(url_entry), 520, -1);
    g_signal_connect(url_entry, "activate", G_CALLBACK(on_entry_activate), NULL);
    gtk_header_bar_set_custom_title(hb, GTK_WIDGET(url_entry));

    GtkWidget *newtab_btn = gtk_button_new_from_icon_name("tab-new", GTK_ICON_SIZE_BUTTON);
    GtkWidget *bookmark_btn = gtk_button_new_from_icon_name("bookmark-new", GTK_ICON_SIZE_BUTTON);
    gtk_widget_set_tooltip_text(bookmark_btn, "Bookmark this page");
    g_signal_connect(newtab_btn,"clicked",G_CALLBACK(on_newtab),NULL);
    g_signal_connect(bookmark_btn,"clicked",G_CALLBACK(on_bookmark),NULL);
    gtk_header_bar_pack_end(hb, newtab_btn);
    gtk_header_bar_pack_end(hb, bookmark_btn);

    // menu button
    GtkWidget *menu_btn = gtk_menu_button_new();
    GtkWidget *menu_img = gtk_image_new_from_icon_name("open-menu", GTK_ICON_SIZE_BUTTON);
    gtk_button_set_image(GTK_BUTTON(menu_btn), menu_img);
    GtkWidget *menu = gtk_menu_new();
    struct { const char *label; GCallback cb; } items[] = {
        {"New Tab (Ctrl+T)", G_CALLBACK(on_newtab)},
        {"Close Tab (Ctrl+W)", G_CALLBACK(on_close_tab)},
        {"Zoom In", G_CALLBACK(on_zoom_in)},
        {"Zoom Out", G_CALLBACK(on_zoom_out)},
        {"History", G_CALLBACK(show_history_dialog)},
        {"Bookmarks (file)", G_CALLBACK(on_bookmark)},
        {"About", G_CALLBACK(show_about)},
        {NULL,NULL}
    };
    for(int i=0; items[i].label; i++){
        GtkWidget *it = gtk_menu_item_new_with_label(items[i].label);
        g_signal_connect(it,"activate", items[i].cb, NULL);
        gtk_menu_shell_append(GTK_MENU_SHELL(menu), it);
    }
    gtk_widget_show_all(menu);
    gtk_menu_button_set_popup(GTK_MENU_BUTTON(menu_btn), menu);
    gtk_header_bar_pack_end(hb, menu_btn);

    // notebook
    notebook = GTK_NOTEBOOK(gtk_notebook_new());
    gtk_notebook_set_scrollable(notebook, TRUE);
    g_signal_connect(notebook, "switch-page", G_CALLBACK(on_switch_page), NULL);

    statusbar = GTK_STATUSBAR(gtk_statusbar_new());
    gtk_statusbar_push(statusbar, 0, "Engine: WebKitGTK 4.1 | C | No Gecko | No Blink | WebKit source cloned");

    GtkWidget *vbox = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_box_pack_start(GTK_BOX(vbox), GTK_WIDGET(notebook), TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(vbox), GTK_WIDGET(statusbar), FALSE, FALSE, 0);
    gtk_container_add(GTK_CONTAINER(main_window), vbox);

    // accel
    GtkAccelGroup *ag = gtk_accel_group_new();
    gtk_window_add_accel_group(main_window, ag);
    // handled via key-press instead

    gtk_widget_show_all(GTK_WIDGET(main_window));
    new_tab(start);
    gtk_main();
    if (history_db) sqlite3_close(history_db);
    return 0;
}
