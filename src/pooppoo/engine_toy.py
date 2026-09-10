"""
Toy HTML engine - pure Python fallback, zero dependency on Gecko/Blink/WebKit.
Used when WebKitGTK is unavailable (e.g., Windows dev without GTK).
Implements: HTTP fetch, basic HTML parsing, simple layout via Tkinter.
This proves the browser does not REQUIRE Blink/Gecko.
"""
import re
import urllib.parse
import requests
from html.parser import HTMLParser

# Very small CSS subset handling
DEFAULT_STYLE = {
    "h1": {"size": 24, "bold": True},
    "h2": {"size": 20, "bold": True},
    "h3": {"size": 16, "bold": True},
    "p": {"size": 11},
    "a": {"size": 11, "color": "#1a0dab", "underline": True},
}

class SimpleHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tokens = []  # list of (type, text, tag, attrs)
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("br", "hr"):
            self.tokens.append(("break", "", tag, attrs))
        elif tag in ("h1","h2","h3","p","div","a","li","span","title","b","strong","i","em"):
            self.current_tag = tag
            self.tokens.append(("open", "", tag, attrs))
        elif tag == "img":
            self.tokens.append(("img", attrs.get("alt"," [image] "), tag, attrs))
        else:
            self.tokens.append(("open", "", tag, attrs))

    def handle_endtag(self, tag):
        self.tokens.append(("close", "", tag, {}))
        self.current_tag = None

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        # collapse whitespace
        text = re.sub(r'\s+', ' ', text)
        self.tokens.append(("text", text, self.current_tag or "span", {}))

def fetch_url(url: str, timeout=10):
    """Fetch URL with requests, return (final_url, html, content_type, error)"""
    if not re.match(r"^https?://", url):
        # search query fallback handled by caller
        url = "https://" + url
    try:
        headers = {"User-Agent": "pooppoo/0.1 WebKit-compat ToyEngine"}
        r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        ctype = r.headers.get("content-type","")
        if "text/html" not in ctype and "text/plain" not in ctype and "application/xhtml" not in ctype:
            # non-html, return as is
            return r.url, f"<h1>Cannot render {ctype}</h1><p>URL: {r.url}</p><p>Download would start in WebKit mode.</p>", ctype, None
        return r.url, r.text, ctype, None
    except Exception as e:
        return url, f"<h1>Failed to load</h1><p>{e}</p>", "text/html", str(e)

def search_url(query: str, engine="https://duckduckgo.com/html/?q=%s"):
    return engine % urllib.parse.quote_plus(query)

def is_probably_url(text: str) -> bool:
    text = text.strip()
    if " " in text and "." not in text:
        return False
    if re.match(r"^https?://", text):
        return True
    if "." in text and " " not in text and len(text) > 3:
        return True
    if text in ("localhost",):
        return True
    return False

def normalize_input(text: str, search_engine="https://duckduckgo.com/html/?q=%s"):
    text = text.strip()
    if not text:
        return "https://duckduckgo.com/"
    if is_probably_url(text):
        if not re.match(r"^https?://", text):
            return "https://" + text
        return text
    return search_url(text, search_engine)

def parse_html(html: str):
    p = SimpleHTMLParser()
    try:
        p.feed(html)
    except Exception:
        pass
    return p.tokens
