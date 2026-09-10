import sys
import os
# allow running as script (python src/pooppoo/__main__.py) and as module (python -m pooppoo)
try:
    from .app import run, HOME_URL
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from pooppoo.app import run, HOME_URL

def main():
    url = sys.argv[1] if len(sys.argv) > 1 else HOME_URL
    if url in ("--help","-h"):
        print("pooppoo browser - WebKit (no Gecko/Blink)")
        print("Usage: pooppoo [url]")
        sys.exit(0)
    run(url)

if __name__ == "__main__":
    main()
