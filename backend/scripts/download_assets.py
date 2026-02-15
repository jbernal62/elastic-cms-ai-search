"""
Downloads ~2200 asset metadata from free, open-license APIs.

Usage:
    cd backend
    python -m scripts.download_assets

API keys are optional for most sources. Set them in .env for higher rate limits.

Sources:
  - Unsplash   (photos)          — needs API key
  - Pexels     (photos + videos) — needs API key
  - Pixabay    (images + videos + music) — needs API key
  - Freesound  (audio/SFX)       — needs API key
  - Wikipedia  (articles)         — no key needed
  - arXiv      (research papers)  — no key needed
  - Gutenberg  (books)            — no key needed
  - Internet Archive (mixed)      — no key needed
"""

import asyncio
import json
import os
import sys
import time
import random
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import settings

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "metadata"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SEARCH_TERMS = [
    "nature", "technology", "business", "health", "travel",
    "food", "science", "art", "music", "sports",
    "architecture", "animals", "ocean", "space", "education",
    "fashion", "finance", "climate", "robotics", "photography",
]

REGIONS = [
    "North America", "South America", "Europe", "Asia",
    "Africa", "Oceania", "Middle East",
]

GEO_POINTS = {
    "North America": {"lat": 39.8, "lon": -98.5},
    "South America": {"lat": -14.2, "lon": -51.9},
    "Europe": {"lat": 50.1, "lon": 9.2},
    "Asia": {"lat": 34.0, "lon": 100.6},
    "Africa": {"lat": 1.6, "lon": 28.0},
    "Oceania": {"lat": -25.3, "lon": 133.8},
    "Middle East": {"lat": 29.3, "lon": 47.5},
}


def random_region():
    weights = [0.25, 0.12, 0.25, 0.18, 0.07, 0.06, 0.07]
    return random.choices(REGIONS, weights=weights, k=1)[0]


def random_date(start_year=2020, end_year=2025):
    y = random.randint(start_year, end_year)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    return f"{y}-{m:02d}-{d:02d}T00:00:00Z"


def save_batch(source: str, items: list[dict]):
    path = DATA_DIR / f"{source}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"  Saved {len(items)} items to {path.name}")


# ════════════════════════════════════════════════════════════════════
#  UNSPLASH — Photos
# ════════════════════════════════════════════════════════════════════
async def fetch_unsplash(client: httpx.AsyncClient) -> list[dict]:
    key = settings.unsplash_access_key
    if not key:
        print("  [Unsplash] No API key — skipping (set UNSPLASH_ACCESS_KEY)")
        return []

    items = []
    for term in SEARCH_TERMS[:15]:
        url = "https://api.unsplash.com/search/photos"
        params = {"query": term, "per_page": 20, "client_id": key}
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            for photo in data.get("results", []):
                region = random_region()
                items.append({
                    "title": photo.get("description") or photo.get("alt_description") or f"Unsplash photo: {term}",
                    "description": photo.get("alt_description", ""),
                    "content_type": "image",
                    "tags": [term] + [t["title"] for t in photo.get("tags", [])[:5]],
                    "category": term,
                    "source": "unsplash",
                    "author": photo.get("user", {}).get("name", "Unknown"),
                    "license": "Unsplash License",
                    "url": photo["urls"]["regular"],
                    "thumbnail_url": photo["urls"]["small"],
                    "preview_url": photo["urls"]["thumb"],
                    "file_type": "jpg",
                    "created_at": photo.get("created_at", random_date()),
                    "region": region,
                    "geo_location": GEO_POINTS[region],
                    "width": photo.get("width", 0),
                    "height": photo.get("height", 0),
                    "view_count": random.randint(10, 5000),
                    "download_count": random.randint(0, 500),
                })
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"  [Unsplash] Error for '{term}': {e}")
    print(f"  [Unsplash] Fetched {len(items)} photos")
    return items


# ════════════════════════════════════════════════════════════════════
#  PEXELS — Photos + Videos
# ════════════════════════════════════════════════════════════════════
async def fetch_pexels(client: httpx.AsyncClient) -> list[dict]:
    key = settings.pexels_api_key
    if not key:
        print("  [Pexels] No API key — skipping (set PEXELS_API_KEY)")
        return []

    headers = {"Authorization": key}
    items = []

    # Photos
    for term in SEARCH_TERMS[:15]:
        url = "https://api.pexels.com/v1/search"
        params = {"query": term, "per_page": 20}
        try:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            for photo in resp.json().get("photos", []):
                region = random_region()
                items.append({
                    "title": photo.get("alt", "") or f"Pexels photo: {term}",
                    "description": photo.get("alt", ""),
                    "content_type": "image",
                    "tags": [term],
                    "category": term,
                    "source": "pexels",
                    "author": photo.get("photographer", "Unknown"),
                    "license": "Pexels License",
                    "url": photo["src"]["original"],
                    "thumbnail_url": photo["src"]["medium"],
                    "preview_url": photo["src"]["tiny"],
                    "file_type": "jpg",
                    "created_at": random_date(),
                    "region": region,
                    "geo_location": GEO_POINTS[region],
                    "width": photo.get("width", 0),
                    "height": photo.get("height", 0),
                    "view_count": random.randint(10, 5000),
                    "download_count": random.randint(0, 500),
                })
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"  [Pexels Photos] Error for '{term}': {e}")

    # Videos
    for term in SEARCH_TERMS[:10]:
        url = "https://api.pexels.com/videos/search"
        params = {"query": term, "per_page": 15}
        try:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            for video in resp.json().get("videos", []):
                region = random_region()
                best_file = video.get("video_files", [{}])[0]
                items.append({
                    "title": f"Pexels video: {term}",
                    "description": f"A video about {term} from Pexels",
                    "content_type": "video",
                    "tags": [term],
                    "category": term,
                    "source": "pexels",
                    "author": video.get("user", {}).get("name", "Unknown"),
                    "license": "Pexels License",
                    "url": best_file.get("link", ""),
                    "thumbnail_url": video.get("image", ""),
                    "preview_url": video.get("image", ""),
                    "file_type": "mp4",
                    "created_at": random_date(),
                    "region": region,
                    "geo_location": GEO_POINTS[region],
                    "duration_seconds": video.get("duration", 0),
                    "width": best_file.get("width", 0),
                    "height": best_file.get("height", 0),
                    "view_count": random.randint(10, 3000),
                    "download_count": random.randint(0, 300),
                })
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"  [Pexels Videos] Error for '{term}': {e}")

    print(f"  [Pexels] Fetched {len(items)} items (photos + videos)")
    return items


# ════════════════════════════════════════════════════════════════════
#  PIXABAY — Images + Videos + Music
# ════════════════════════════════════════════════════════════════════
async def fetch_pixabay(client: httpx.AsyncClient) -> list[dict]:
    key = settings.pixabay_api_key
    if not key:
        print("  [Pixabay] No API key — skipping (set PIXABAY_API_KEY)")
        return []

    items = []

    # Images
    for term in SEARCH_TERMS[:10]:
        url = "https://pixabay.com/api/"
        params = {"key": key, "q": term, "per_page": 20, "image_type": "photo"}
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            for hit in resp.json().get("hits", []):
                region = random_region()
                items.append({
                    "title": hit.get("tags", term).split(",")[0].strip(),
                    "description": hit.get("tags", ""),
                    "content_type": "image",
                    "tags": [t.strip() for t in hit.get("tags", "").split(",")],
                    "category": term,
                    "source": "pixabay",
                    "author": hit.get("user", "Unknown"),
                    "license": "Pixabay License",
                    "url": hit.get("largeImageURL", ""),
                    "thumbnail_url": hit.get("webformatURL", ""),
                    "preview_url": hit.get("previewURL", ""),
                    "file_type": "jpg",
                    "created_at": random_date(),
                    "region": region,
                    "geo_location": GEO_POINTS[region],
                    "width": hit.get("imageWidth", 0),
                    "height": hit.get("imageHeight", 0),
                    "view_count": hit.get("views", 0),
                    "download_count": hit.get("downloads", 0),
                })
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"  [Pixabay Images] Error for '{term}': {e}")

    # Videos
    for term in SEARCH_TERMS[:8]:
        url = "https://pixabay.com/api/videos/"
        params = {"key": key, "q": term, "per_page": 10}
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            for hit in resp.json().get("hits", []):
                region = random_region()
                vids = hit.get("videos", {})
                medium = vids.get("medium", {})
                items.append({
                    "title": hit.get("tags", term).split(",")[0].strip(),
                    "description": hit.get("tags", ""),
                    "content_type": "video",
                    "tags": [t.strip() for t in hit.get("tags", "").split(",")],
                    "category": term,
                    "source": "pixabay",
                    "author": hit.get("user", "Unknown"),
                    "license": "Pixabay License",
                    "url": medium.get("url", ""),
                    "thumbnail_url": f"https://i.vimeocdn.com/video/{hit.get('picture_id', '')}_295x166.jpg",
                    "preview_url": "",
                    "file_type": "mp4",
                    "created_at": random_date(),
                    "region": region,
                    "geo_location": GEO_POINTS[region],
                    "duration_seconds": hit.get("duration", 0),
                    "width": medium.get("width", 0),
                    "height": medium.get("height", 0),
                    "view_count": hit.get("views", 0),
                    "download_count": hit.get("downloads", 0),
                })
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"  [Pixabay Videos] Error for '{term}': {e}")

    print(f"  [Pixabay] Fetched {len(items)} items")
    return items


# ════════════════════════════════════════════════════════════════════
#  FREESOUND — Audio / SFX
# ════════════════════════════════════════════════════════════════════
async def fetch_freesound(client: httpx.AsyncClient) -> list[dict]:
    key = settings.freesound_api_key
    if not key:
        print("  [Freesound] No API key — skipping (set FREESOUND_API_KEY)")
        return []

    items = []
    for term in SEARCH_TERMS[:10]:
        url = "https://freesound.org/apiv2/search/text/"
        params = {
            "query": term,
            "page_size": 20,
            "fields": "id,name,description,tags,username,license,duration,previews,created",
            "token": key,
        }
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            for sound in resp.json().get("results", []):
                region = random_region()
                previews = sound.get("previews", {})
                items.append({
                    "title": sound.get("name", f"Sound: {term}"),
                    "description": (sound.get("description", "") or "")[:500],
                    "content_type": "audio",
                    "tags": sound.get("tags", [term])[:10],
                    "category": term,
                    "source": "freesound",
                    "author": sound.get("username", "Unknown"),
                    "license": sound.get("license", "CC"),
                    "url": previews.get("preview-hq-mp3", ""),
                    "thumbnail_url": "",
                    "preview_url": previews.get("preview-lq-mp3", ""),
                    "file_type": "mp3",
                    "created_at": sound.get("created", random_date()),
                    "region": region,
                    "geo_location": GEO_POINTS[region],
                    "duration_seconds": int(sound.get("duration", 0)),
                    "view_count": random.randint(10, 2000),
                    "download_count": random.randint(0, 300),
                })
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"  [Freesound] Error for '{term}': {e}")

    print(f"  [Freesound] Fetched {len(items)} audio files")
    return items


# ════════════════════════════════════════════════════════════════════
#  WIKIPEDIA — Articles
# ════════════════════════════════════════════════════════════════════
async def fetch_wikipedia(client: httpx.AsyncClient) -> list[dict]:
    items = []
    for term in SEARCH_TERMS:
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": term,
            "srlimit": 20,
            "format": "json",
        }
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            for article in resp.json().get("query", {}).get("search", []):
                region = random_region()
                title = article["title"]
                snippet = article.get("snippet", "").replace('<span class="searchmatch">', "").replace("</span>", "")
                items.append({
                    "title": title,
                    "description": snippet,
                    "content_type": "article",
                    "tags": [term, "wikipedia", "encyclopedia"],
                    "category": term,
                    "source": "wikipedia",
                    "author": "Wikipedia Contributors",
                    "license": "CC BY-SA 4.0",
                    "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    "thumbnail_url": "",
                    "preview_url": "",
                    "file_type": "html",
                    "created_at": article.get("timestamp", random_date()),
                    "region": region,
                    "geo_location": GEO_POINTS[region],
                    "view_count": random.randint(100, 50000),
                    "download_count": random.randint(0, 100),
                })
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"  [Wikipedia] Error for '{term}': {e}")

    print(f"  [Wikipedia] Fetched {len(items)} articles")
    return items


# ════════════════════════════════════════════════════════════════════
#  ARXIV — Research Papers
# ════════════════════════════════════════════════════════════════════
async def fetch_arxiv(client: httpx.AsyncClient) -> list[dict]:
    items = []
    science_terms = [
        "machine learning", "neural network", "climate change",
        "quantum computing", "renewable energy", "artificial intelligence",
        "deep learning", "natural language processing", "computer vision",
        "robotics", "genomics", "astrophysics", "materials science",
        "blockchain", "cybersecurity",
    ]
    for term in science_terms:
        url = "https://export.arxiv.org/api/query"
        params = {"search_query": f"all:{term}", "start": 0, "max_results": 20}
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns):
                region = random_region()
                title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
                summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")[:500]
                authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
                published = entry.find("atom:published", ns).text
                link = entry.find("atom:id", ns).text
                items.append({
                    "title": title,
                    "description": summary,
                    "content_type": "paper",
                    "tags": [term, "research", "arxiv"],
                    "category": "science",
                    "source": "arxiv",
                    "author": authors[0] if authors else "Unknown",
                    "license": "arXiv License",
                    "url": link,
                    "thumbnail_url": "",
                    "preview_url": link.replace("abs", "pdf"),
                    "file_type": "pdf",
                    "created_at": published,
                    "region": region,
                    "geo_location": GEO_POINTS[region],
                    "view_count": random.randint(50, 10000),
                    "download_count": random.randint(10, 5000),
                })
            await asyncio.sleep(1.0)  # arXiv rate limit is strict
        except Exception as e:
            print(f"  [arXiv] Error for '{term}': {e}")

    print(f"  [arXiv] Fetched {len(items)} papers")
    return items


# ════════════════════════════════════════════════════════════════════
#  PROJECT GUTENBERG — Books
# ════════════════════════════════════════════════════════════════════
async def fetch_gutenberg(client: httpx.AsyncClient) -> list[dict]:
    items = []
    topics = [
        "adventure", "romance", "science", "history", "philosophy",
        "poetry", "fiction", "mystery", "fantasy", "biography",
    ]
    for term in topics:
        url = "https://gutendex.com/books/"
        params = {"search": term, "page": 1}
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            for book in resp.json().get("results", [])[:20]:
                region = random_region()
                authors = book.get("authors", [])
                author_name = authors[0]["name"] if authors else "Unknown"
                formats = book.get("formats", {})
                txt_url = formats.get("text/plain; charset=utf-8", "") or formats.get("text/plain", "")
                cover = formats.get("image/jpeg", "")
                subjects = book.get("subjects", [])
                items.append({
                    "title": book.get("title", "Untitled Book"),
                    "description": f"A book about {term} by {author_name}. Subjects: {'; '.join(subjects[:3])}",
                    "content_type": "book",
                    "tags": [term, "book", "literature"] + [s.lower()[:30] for s in subjects[:3]],
                    "category": term,
                    "source": "gutenberg",
                    "author": author_name,
                    "license": "Public Domain",
                    "url": txt_url,
                    "thumbnail_url": cover,
                    "preview_url": cover,
                    "file_type": "txt",
                    "created_at": random_date(1990, 2020),
                    "region": region,
                    "geo_location": GEO_POINTS[region],
                    "view_count": random.randint(50, 20000),
                    "download_count": random.randint(10, 8000),
                })
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"  [Gutenberg] Error for '{term}': {e}")

    print(f"  [Gutenberg] Fetched {len(items)} books")
    return items


# ════════════════════════════════════════════════════════════════════
#  INTERNET ARCHIVE — Mixed (books, audio, video, texts)
# ════════════════════════════════════════════════════════════════════
async def fetch_internet_archive(client: httpx.AsyncClient) -> list[dict]:
    items = []
    media_types = [
        ("texts", "document"),
        ("audio", "audio"),
        ("movies", "video"),
        ("image", "image"),
    ]

    for media_type, content_type in media_types:
        for term in SEARCH_TERMS[:8]:
            url = "https://archive.org/advancedsearch.php"
            params = {
                "q": f"{term} AND mediatype:{media_type}",
                "fl[]": "identifier,title,description,creator,date,mediatype,downloads",
                "rows": 10,
                "page": 1,
                "output": "json",
            }
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                docs = resp.json().get("response", {}).get("docs", [])
                for doc in docs:
                    region = random_region()
                    identifier = doc.get("identifier", "")
                    items.append({
                        "title": doc.get("title", f"Archive: {term}"),
                        "description": (doc.get("description", "") or f"Internet Archive {content_type} about {term}")[:500],
                        "content_type": content_type,
                        "tags": [term, "archive", media_type],
                        "category": term,
                        "source": "internet_archive",
                        "author": doc.get("creator", "Unknown") if isinstance(doc.get("creator"), str) else "Various",
                        "license": "Public Domain / Open",
                        "url": f"https://archive.org/details/{identifier}",
                        "thumbnail_url": f"https://archive.org/services/img/{identifier}",
                        "preview_url": f"https://archive.org/details/{identifier}",
                        "file_type": {"texts": "pdf", "audio": "mp3", "movies": "mp4", "image": "jpg"}[media_type],
                        "created_at": doc.get("date", random_date()),
                        "region": region,
                        "geo_location": GEO_POINTS[region],
                        "view_count": random.randint(10, 5000),
                        "download_count": doc.get("downloads", random.randint(0, 1000)),
                    })
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"  [Archive] Error for '{media_type}/{term}': {e}")

    print(f"  [Internet Archive] Fetched {len(items)} items")
    return items


# ════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════
async def main():
    print("=" * 60)
    print("  CMS AI Search — Asset Download Script")
    print("=" * 60)

    all_items = []

    headers = {"User-Agent": "CMSAISearchDemo/1.0 (contact@example.com) python-httpx"}
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
        # APIs that need keys
        print("\n[1/8] Unsplash (photos)...")
        all_items.extend(await fetch_unsplash(client))

        print("[2/8] Pexels (photos + videos)...")
        all_items.extend(await fetch_pexels(client))

        print("[3/8] Pixabay (images + videos + music)...")
        all_items.extend(await fetch_pixabay(client))

        print("[4/8] Freesound (audio/SFX)...")
        all_items.extend(await fetch_freesound(client))

        # APIs that don't need keys
        print("[5/8] Wikipedia (articles)...")
        all_items.extend(await fetch_wikipedia(client))

        print("[6/8] arXiv (research papers)...")
        all_items.extend(await fetch_arxiv(client))

        print("[7/8] Project Gutenberg (books)...")
        all_items.extend(await fetch_gutenberg(client))

        print("[8/8] Internet Archive (mixed)...")
        all_items.extend(await fetch_internet_archive(client))

    # Save combined metadata
    save_batch("all_assets", all_items)

    # Summary
    print("\n" + "=" * 60)
    print(f"  TOTAL ASSETS DOWNLOADED: {len(all_items)}")
    print("=" * 60)

    by_type = {}
    by_source = {}
    for item in all_items:
        ct = item["content_type"]
        src = item["source"]
        by_type[ct] = by_type.get(ct, 0) + 1
        by_source[src] = by_source.get(src, 0) + 1

    print("\n  By content type:")
    for ct, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"    {ct:12s} {count:5d}")

    print("\n  By source:")
    for src, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"    {src:20s} {count:5d}")

    print(f"\n  Metadata saved to: {DATA_DIR / 'all_assets.json'}")


if __name__ == "__main__":
    asyncio.run(main())
