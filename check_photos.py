"""check_photos.py - finds out why car photos are not loading.   Run:  .venv/bin/python check_photos.py"""
import httpx

from photos import HEADERS, WIKI_TITLES

title = WIKI_TITLES["Toyota Corolla"]
print("1. Can we reach Wikipedia?")
try:
    r = httpx.get("https://en.wikipedia.org/api/rest_v1/page/summary/" + title.replace(" ", "_"), headers=HEADERS, timeout=20, follow_redirects=True)
    print("   status", r.status_code)
    src = (r.json().get("originalimage") or {}).get("source")
    print("   main picture:", src)
except Exception as problem:
    raise SystemExit(f"   FAILED: {problem!r}\n   (No internet, a VPN/firewall, or a certificate problem. Paste this to Claude.)")

print("2. Can we read its licence from Commons?")
try:
    from photos import _commons_info
    with httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True) as c:
        info = _commons_info(c, src)
    print("   result:", info)
except Exception as problem:
    raise SystemExit(f"   FAILED: {problem!r}")

print("3. Downloading the picture and saving it...")
import photos
photos.CACHE_DIR.mkdir(exist_ok=True)
for f in photos.CACHE_DIR.glob("toyota-corolla.*"):
    f.unlink()
print("   saved!" if photos._download("Toyota Corolla") else "   no free photo found for the Corolla")
