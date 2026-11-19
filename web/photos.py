"""photos.py - finds a real photo of each car on Wikimedia Commons (free to use, with credit).

How it works, in plain words:
  1. We know which Wikipedia article describes each car (WIKI_TITLES below).
  2. We ask Wikipedia for that article's main picture.
  3. We only accept pictures stored on Wikimedia Commons, because those carry a free licence.
     (Pictures stored directly on Wikipedia are often "fair use" and NOT free, so we skip them.)
  4. We ask Commons who took it and which licence it has, so the website can show a credit.
  5. We save the picture and the credit in the photo_cache/ folder, so each car is fetched only once.

If anything fails (no internet, no free picture), the website shows a plain drawing instead.
"""
import json
import re
import threading
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

CACHE_DIR = Path(__file__).parent / "photo_cache"
HEADERS = {"User-Agent": "RoarwellMotorsPracticeProject/1.0 (learning project; contact: none)"}
WIDTH = 960

# car name -> Wikipedia article title (the part of the web address after /wiki/)
WIKI_TITLES = {
    "Toyota Corolla": "Toyota Corolla",
    "Toyota Camry": "Toyota Camry",
    "Toyota Prius": "Toyota Prius",
    "Toyota RAV4 Hybrid": "Toyota RAV4",
    "Toyota Grand Highlander": "Toyota Grand Highlander",
    "Toyota Sienna": "Toyota Sienna",
    "Toyota Tacoma": "Toyota Tacoma",
    "Honda Civic": "Honda Civic",
    "Honda HR-V": "Honda HR-V",
    "Honda CR-V": "Honda CR-V",
    "Honda CR-V Hybrid": "Honda CR-V",
    "Honda Odyssey": "Honda Odyssey (North America)",
    "Hyundai Elantra": "Hyundai Elantra",
    "Hyundai Elantra Hybrid": "Hyundai Elantra",
    "Hyundai Tucson Hybrid": "Hyundai Tucson",
    "Hyundai Palisade": "Hyundai Palisade",
    "Hyundai Ioniq 5": "Hyundai Ioniq 5",
    "Kia Sportage Hybrid": "Kia Sportage",
    "Kia Telluride": "Kia Telluride",
    "Kia Carnival": "Kia Carnival",
    "Ford Maverick Hybrid": "Ford Maverick (2022)",
    "Ford Escape Hybrid": "Ford Escape",
    "Ford F-150": "Ford F-Series (thirteenth generation)",
    "Ford Mustang Mach-E": "Ford Mustang Mach-E",
    "Tesla Model 3": "Tesla Model 3",
    "Tesla Model Y": "Tesla Model Y",
    "Mazda3 Hatchback": "Mazda3",
    "Mazda CX-5": "Mazda CX-5",
    "1969 Ford Mustang Mach 1": "Ford Mustang (first generation)",
    "1965 Ford Mustang": "Ford Mustang (first generation)",
    "1969 Chevrolet Camaro": "Chevrolet Camaro (first generation)",
}

_locks = {}
_locks_guard = threading.Lock()


def _lock_for(key):
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def _clean(text):
    """Commons credits contain HTML tags; keep just the words."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text or "")).strip()


def _summary_image(client, title):
    """Ask Wikipedia for the article's main image address (or None)."""
    r = client.get("https://en.wikipedia.org/api/rest_v1/page/summary/" + title.replace(" ", "_"))
    if r.status_code >= 429:
        raise RuntimeError("Wikipedia is busy, try later")   # temporary: do not remember as a miss
    if r.status_code != 200:
        return None
    return (r.json().get("originalimage") or {}).get("source")


def _commons_info(client, source_url):
    """For a Commons image address, return (thumbnail address, credit dict) or None."""
    if "/wikipedia/commons/" not in source_url:
        return None                                        # not on Commons -> not guaranteed free
    parts = urlparse(source_url).path.split("/")
    # thumbnail addresses look like .../commons/thumb/a/ab/File.jpg/320px-File.jpg
    filename = unquote(parts[parts.index("thumb") + 3] if "thumb" in parts else parts[-1])
    r = client.get("https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "format": "json", "prop": "imageinfo", "titles": "File:" + filename,
        "iiprop": "url|extmetadata", "iiurlwidth": WIDTH,
    })
    pages = r.json().get("query", {}).get("pages", {})
    info = next(iter(pages.values()), {}).get("imageinfo")
    if not info:
        return None
    info = info[0]
    meta = info.get("extmetadata", {})
    free = meta.get("LicenseShortName", {}).get("value", "")
    if not free or "fair use" in free.lower() or "non-free" in free.lower():
        return None
    credit = {
        "author": _clean(meta.get("Artist", {}).get("value")) or "Unknown author",
        "license": _clean(free),
        "page": info.get("descriptionurl", ""),
    }
    return info.get("thumburl") or info.get("url"), credit


def _download(car_name):
    """Fetch one car's photo and credit into the cache. Returns True on success."""
    title = WIKI_TITLES.get(car_name)
    if not title:
        return False
    with httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True) as client:
        source = _summary_image(client, title)
        found = _commons_info(client, source) if source else None
        if not found:
            return False
        url, credit = found
        img = client.get(url)
        if img.status_code != 200 or not img.headers.get("content-type", "").startswith("image/"):
            return False
    from slug import slugify
    key = slugify(car_name)
    CACHE_DIR.mkdir(exist_ok=True)
    (CACHE_DIR / f"{key}.jpg").write_bytes(img.content)
    (CACHE_DIR / f"{key}.json").write_text(json.dumps(credit))
    return True


def get_photo(car_name):
    """Return (path to the picture, credit dict) or None. Fetches once, then uses the cache."""
    from slug import slugify
    key = slugify(car_name)
    jpg, meta = CACHE_DIR / f"{key}.jpg", CACHE_DIR / f"{key}.json"
    if jpg.exists() and meta.exists():
        return jpg, json.loads(meta.read_text())
    miss = CACHE_DIR / f"{key}.miss"
    if miss.exists():
        return None
    with _lock_for(key):
        if not jpg.exists():
            try:
                ok = _download(car_name)
            except Exception:
                return None                                # network trouble: try again next time
            if not ok:
                CACHE_DIR.mkdir(exist_ok=True)
                miss.write_text("no free photo found")      # remember, so we stop asking
                return None
    return jpg, json.loads(meta.read_text())
