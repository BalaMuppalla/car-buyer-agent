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
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

from cars import slugify

CACHE_DIR = Path(__file__).parent / "photo_cache"
HEADERS = {"User-Agent": "RoarwellMotors/1.0 (student practice project; https://github.com/) python-httpx"}
MISS_LIFETIME = 3600          # a "no free photo" note is forgotten after an hour, so we retry later
_slots = threading.Semaphore(3)   # be polite: at most 3 downloads at the same time
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
    "Subaru Outback": "Subaru Outback",
    "Subaru Crosstrek": "Subaru Crosstrek",
    "Chevrolet Equinox": "Chevrolet Equinox",
    "Chevrolet Silverado 1500": "Chevrolet Silverado 1500",
    "Ram 1500": "Ram 1500",
    "Jeep Wrangler": "Jeep Wrangler (JL)",
    "Nissan Rogue": "Nissan Rogue",
    "Volkswagen Jetta": "Volkswagen Jetta",
    "BMW 3 Series": "BMW 3 Series (G20)",
    "Lexus RX Hybrid": "Lexus RX",
    "Kia EV6": "Kia EV6",
    "1967 Chevrolet Corvette Stingray": "Chevrolet Corvette (C2)",
    "1970 Dodge Challenger R/T": "Dodge Challenger (first generation)",
    "1957 Chevrolet Bel Air": "Chevrolet Bel Air",
}

_locks = {}
_locks_guard = threading.Lock()


def _lock_for(key):
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def _clean(text):
    """Commons credits contain HTML tags; keep just the words."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text or "")).strip()


def _get(client, url, **kwargs):
    """GET with a few polite retries when Wikimedia says 'slow down' (429) or is briefly down (5xx)."""
    for attempt in range(4):
        r = client.get(url, **kwargs)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(1.5 * (attempt + 1))
            continue
        return r
    raise RuntimeError(f"Wikimedia kept answering {r.status_code} for {url}")


def _summary_image(client, title):
    """Ask Wikipedia for the article's main image address (or None)."""
    r = _get(client, "https://en.wikipedia.org/api/rest_v1/page/summary/" + title.replace(" ", "_"))
    if r.status_code == 404:
        return None                                        # no such article: a real "miss"
    r.raise_for_status()                                   # anything else odd = a problem, not a miss
    return (r.json().get("originalimage") or {}).get("source")


def _commons_info(client, source_url):
    """For a Commons image address, return (thumbnail address, credit dict) or None."""
    if "/wikipedia/commons/" not in source_url:
        return None                                        # not on Commons -> not guaranteed free
    parts = urlparse(source_url).path.split("/")
    # thumbnail addresses look like .../commons/thumb/a/ab/File.jpg/320px-File.jpg
    filename = unquote(parts[parts.index("thumb") + 3] if "thumb" in parts else parts[-1])
    r = _get(client, "https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "format": "json", "prop": "imageinfo", "titles": "File:" + filename,
        "iiprop": "url|extmetadata", "iiurlwidth": WIDTH,
    })
    r.raise_for_status()
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
        img = _get(client, url)
        img.raise_for_status()
        if not img.headers.get("content-type", "").startswith("image/"):
            raise RuntimeError("the photo address did not return a picture")
    key = slugify(car_name)
    CACHE_DIR.mkdir(exist_ok=True)
    (CACHE_DIR / f"{key}.jpg").write_bytes(img.content)
    (CACHE_DIR / f"{key}.json").write_text(json.dumps(credit))
    return True


def get_photo(car_name):
    """Return (path to the picture, credit dict) or None. Fetches once, then uses the cache."""
    key = slugify(car_name)
    jpg, meta = CACHE_DIR / f"{key}.jpg", CACHE_DIR / f"{key}.json"
    if jpg.exists() and meta.exists():
        return jpg, json.loads(meta.read_text())
    miss = CACHE_DIR / f"{key}.miss"
    if miss.exists() and time.time() - miss.stat().st_mtime < MISS_LIFETIME:
        return None
    with _lock_for(key), _slots:
        if not jpg.exists():
            try:
                ok = _download(car_name)
            except Exception as problem:
                print(f"[photos] {car_name}: could not download ({problem!r}). Will retry next time.")
                return None                                # network trouble: try again next time
            if not ok:
                CACHE_DIR.mkdir(exist_ok=True)
                miss.write_text("no free photo found")      # remember for a while, so we stop asking
                print(f"[photos] {car_name}: no free-licence photo found on Wikimedia Commons.")
                return None
    return jpg, json.loads(meta.read_text())
