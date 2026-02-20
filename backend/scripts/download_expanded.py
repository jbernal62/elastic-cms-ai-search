"""
Expanded asset download — fetches ~6000+ items from multiple sources.

Usage:
    cd backend
    python -m scripts.download_expanded
"""

import asyncio
import json
import os
import sys
import random
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "metadata"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SEARCH_TERMS = [
    "nature", "technology", "business", "health", "travel",
    "food", "science", "art", "music", "sports",
    "architecture", "animals", "ocean", "space", "education",
    "fashion", "finance", "climate", "robotics", "photography",
    "mountains", "desert", "forest", "city", "sunset",
    "cooking", "gardening", "meditation", "yoga", "fitness",
    "astronomy", "biology", "chemistry", "physics", "mathematics",
    "history", "culture", "dance", "theater", "cinema",
    "programming", "cybersecurity", "cloud computing", "data science", "blockchain",
    "renewable energy", "electric vehicles", "sustainability", "recycling", "wildlife",
    "psychology", "neuroscience", "genetics", "medicine", "surgery",
    "painting", "sculpture", "pottery", "calligraphy", "origami",
    "jazz", "classical music", "electronic music", "hip hop", "rock music",
    "football", "basketball", "tennis", "swimming", "cycling",
]

REGIONS = ["North America", "South America", "Europe", "Asia", "Africa", "Oceania", "Middle East"]
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


def random_date(start_year=2018, end_year=2025):
    y = random.randint(start_year, end_year)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    return f"{y}-{m:02d}-{d:02d}T00:00:00Z"


total_items: list[dict] = []


async def fetch_unsplash(client: httpx.AsyncClient):
    key = os.environ.get("UNSPLASH_ACCESS_KEY", "sdMamGVHAsltX4jgVP6b1nbQ8kzjNKTBsjfkw3UOoSQ")
    count = 0
    for term in SEARCH_TERMS[:40]:
        for page in [1, 2, 3]:
            try:
                resp = await client.get(
                    "https://api.unsplash.com/search/photos",
                    params={"query": term, "per_page": 30, "page": page, "client_id": key},
                )
                resp.raise_for_status()
                for photo in resp.json().get("results", []):
                    region = random_region()
                    total_items.append({
                        "title": photo.get("description") or photo.get("alt_description") or f"Unsplash: {term}",
                        "description": photo.get("alt_description", ""),
                        "content_type": "image",
                        "tags": [term] + [t["title"] for t in photo.get("tags", [])[:5]],
                        "category": term, "source": "unsplash",
                        "author": photo.get("user", {}).get("name", "Unknown"),
                        "license": "Unsplash License",
                        "url": photo["urls"]["regular"],
                        "thumbnail_url": photo["urls"]["small"],
                        "preview_url": photo["urls"]["thumb"],
                        "file_type": "jpg",
                        "created_at": photo.get("created_at", random_date()),
                        "region": region, "geo_location": GEO_POINTS[region],
                        "width": photo.get("width", 0), "height": photo.get("height", 0),
                        "view_count": random.randint(10, 5000),
                        "download_count": random.randint(0, 500),
                    })
                    count += 1
                await asyncio.sleep(0.4)
            except Exception as e:
                if "403" in str(e) or "429" in str(e):
                    print(f"  [Unsplash] Rate limited at {term} page {page}, waiting...")
                    await asyncio.sleep(10)
    print(f"  [Unsplash] {count} photos")



async def fetch_wikipedia(client: httpx.AsyncClient):
    count = 0
    for term in SEARCH_TERMS:
        for offset in [0, 20, 40]:
            try:
                resp = await client.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={"action": "query", "list": "search", "srsearch": term,
                            "srlimit": 20, "sroffset": offset, "format": "json"},
                )
                resp.raise_for_status()
                for article in resp.json().get("query", {}).get("search", []):
                    region = random_region()
                    title = article["title"]
                    snippet = article.get("snippet", "")
                    snippet = snippet.replace('<span class="searchmatch">', "").replace("</span>", "")
                    total_items.append({
                        "title": title, "description": snippet,
                        "content_type": "article", "tags": [term, "wikipedia", "encyclopedia"],
                        "category": term, "source": "wikipedia",
                        "author": "Wikipedia Contributors", "license": "CC BY-SA 4.0",
                        "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                        "thumbnail_url": "", "preview_url": "", "file_type": "html",
                        "created_at": article.get("timestamp", random_date()),
                        "region": region, "geo_location": GEO_POINTS[region],
                        "view_count": random.randint(100, 50000),
                        "download_count": random.randint(0, 100),
                    })
                    count += 1
                await asyncio.sleep(0.2)
            except Exception:
                pass
    print(f"  [Wikipedia] {count} articles")


async def fetch_arxiv(client: httpx.AsyncClient):
    count = 0
    arxiv_terms = [
        "machine learning", "neural network", "climate change", "quantum computing",
        "renewable energy", "artificial intelligence", "deep learning",
        "natural language processing", "computer vision", "robotics",
        "genomics", "astrophysics", "materials science", "blockchain",
        "cybersecurity", "large language models", "reinforcement learning",
        "graph neural networks", "federated learning", "transformers attention",
        "generative adversarial network", "protein folding", "drug discovery",
        "autonomous driving", "speech recognition", "recommendation systems",
        "time series forecasting", "anomaly detection", "transfer learning",
        "edge computing",
    ]
    for term in arxiv_terms:
        try:
            resp = await client.get(
                "https://export.arxiv.org/api/query",
                params={"search_query": f"all:{term}", "start": 0, "max_results": 30},
            )
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
                total_items.append({
                    "title": title, "description": summary,
                    "content_type": "paper", "tags": [term, "research", "arxiv"],
                    "category": "science", "source": "arxiv",
                    "author": authors[0] if authors else "Unknown",
                    "license": "arXiv License",
                    "url": link, "thumbnail_url": "",
                    "preview_url": link.replace("abs", "pdf"),
                    "file_type": "pdf",
                    "created_at": published,
                    "region": region, "geo_location": GEO_POINTS[region],
                    "view_count": random.randint(50, 10000),
                    "download_count": random.randint(10, 5000),
                })
                count += 1
            await asyncio.sleep(3.0)  # arXiv strict rate limit
        except Exception as e:
            print(f"  [arXiv] Error for {term}: {e}")
    print(f"  [arXiv] {count} papers")


async def fetch_gutenberg(client: httpx.AsyncClient):
    count = 0
    topics = [
        "adventure", "romance", "science", "history", "philosophy",
        "poetry", "fiction", "mystery", "fantasy", "biography",
        "war", "love", "death", "nature", "religion",
        "politics", "education", "travel", "humor", "drama",
    ]
    for term in topics:
        try:
            resp = await client.get("https://gutendex.com/books/", params={"search": term, "page": 1})
            resp.raise_for_status()
            for book in resp.json().get("results", [])[:32]:
                region = random_region()
                authors = book.get("authors", [])
                author_name = authors[0]["name"] if authors else "Unknown"
                formats = book.get("formats", {})
                txt_url = formats.get("text/plain; charset=utf-8", "") or formats.get("text/plain", "")
                cover = formats.get("image/jpeg", "")
                subjects = book.get("subjects", [])
                total_items.append({
                    "title": book.get("title", "Untitled Book"),
                    "description": f"A book about {term} by {author_name}. Subjects: {'; '.join(subjects[:3])}",
                    "content_type": "book",
                    "tags": [term, "book", "literature"] + [s.lower()[:30] for s in subjects[:3]],
                    "category": term, "source": "gutenberg",
                    "author": author_name, "license": "Public Domain",
                    "url": txt_url, "thumbnail_url": cover, "preview_url": cover,
                    "file_type": "txt",
                    "created_at": random_date(1990, 2020),
                    "region": region, "geo_location": GEO_POINTS[region],
                    "view_count": random.randint(50, 20000),
                    "download_count": random.randint(10, 8000),
                })
                count += 1
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"  [Gutenberg] Error: {e}")
    print(f"  [Gutenberg] {count} books")


async def fetch_internet_archive(client: httpx.AsyncClient):
    count = 0
    media_types = [("texts", "document"), ("audio", "audio"), ("movies", "video"), ("image", "image")]
    for media_type, content_type in media_types:
        for term in SEARCH_TERMS[:25]:
            try:
                resp = await client.get(
                    "https://archive.org/advancedsearch.php",
                    params={
                        "q": f"{term} AND mediatype:{media_type}",
                        "fl[]": "identifier,title,description,creator,date,mediatype,downloads",
                        "rows": 20, "page": 1, "output": "json",
                    },
                )
                resp.raise_for_status()
                for doc in resp.json().get("response", {}).get("docs", []):
                    region = random_region()
                    identifier = doc.get("identifier", "")
                    total_items.append({
                        "title": doc.get("title", f"Archive: {term}"),
                        "description": (doc.get("description", "") or f"Internet Archive {content_type} about {term}")[:500],
                        "content_type": content_type,
                        "tags": [term, "archive", media_type],
                        "category": term, "source": "internet_archive",
                        "author": doc.get("creator", "Unknown") if isinstance(doc.get("creator"), str) else "Various",
                        "license": "Public Domain / Open",
                        "url": f"https://archive.org/details/{identifier}",
                        "thumbnail_url": f"https://archive.org/services/img/{identifier}",
                        "preview_url": f"https://archive.org/details/{identifier}",
                        "file_type": {"texts": "pdf", "audio": "mp3", "movies": "mp4", "image": "jpg"}[media_type],
                        "created_at": doc.get("date", random_date()),
                        "region": region, "geo_location": GEO_POINTS[region],
                        "view_count": random.randint(10, 5000),
                        "download_count": doc.get("downloads", random.randint(0, 1000)),
                    })
                    count += 1
                await asyncio.sleep(0.3)
            except Exception:
                pass
    print(f"  [Internet Archive] {count} items")


async def fetch_freesound(client: httpx.AsyncClient):
    key = os.environ.get("FREESOUND_API_KEY", "tq1bLSqJ2RC0ZYlgBjeA2WExu5GFcPSm6wtGO15h")
    count = 0
    for term in SEARCH_TERMS[:25]:
        try:
            resp = await client.get(
                "https://freesound.org/apiv2/search/text/",
                params={
                    "query": term, "page_size": 30,
                    "fields": "id,name,description,tags,username,license,duration,previews,created",
                    "token": key,
                },
            )
            resp.raise_for_status()
            for sound in resp.json().get("results", []):
                region = random_region()
                previews = sound.get("previews", {})
                total_items.append({
                    "title": sound.get("name", f"Sound: {term}"),
                    "description": (sound.get("description", "") or "")[:500],
                    "content_type": "audio", "tags": sound.get("tags", [term])[:10],
                    "category": term, "source": "freesound",
                    "author": sound.get("username", "Unknown"),
                    "license": sound.get("license", "CC"),
                    "url": previews.get("preview-hq-mp3", ""),
                    "thumbnail_url": "", "preview_url": previews.get("preview-lq-mp3", ""),
                    "file_type": "mp3",
                    "created_at": sound.get("created", random_date()),
                    "region": region, "geo_location": GEO_POINTS[region],
                    "duration_seconds": int(sound.get("duration", 0)),
                    "view_count": random.randint(10, 2000),
                    "download_count": random.randint(0, 300),
                })
                count += 1
            await asyncio.sleep(0.5)
        except Exception:
            pass
    print(f"  [Freesound] {count} audio files")


async def main():
    print("=" * 60)
    print("  CMS AI Search — Expanded Asset Download")
    print("=" * 60)

    headers = {"User-Agent": "CMSAISearchDemo/1.0 python-httpx"}
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
        print("\n[1/6] Unsplash (photos)...")
        await fetch_unsplash(client)

        print("[2/6] Wikipedia (articles)...")
        await fetch_wikipedia(client)

        print("[3/6] arXiv (research papers)...")
        await fetch_arxiv(client)

        print("[4/6] Project Gutenberg (books)...")
        await fetch_gutenberg(client)

        print("[5/6] Internet Archive (mixed)...")
        await fetch_internet_archive(client)

        print("[6/6] Freesound (audio)...")
        await fetch_freesound(client)

    # Deduplicate by URL
    seen_urls: set[str] = set()
    deduped: list[dict] = []
    for item in total_items:
        url = item.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduped.append(item)
        elif not url:
            deduped.append(item)

    print(f"\nTotal before dedup: {len(total_items)}")
    print(f"Total after dedup:  {len(deduped)}")

    out_path = DATA_DIR / "all_assets.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)
    print(f"Saved to {out_path}")

    # Summary
    by_source: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for item in deduped:
        by_source[item["source"]] = by_source.get(item["source"], 0) + 1
        by_type[item["content_type"]] = by_type.get(item["content_type"], 0) + 1

    print("\nBy source:")
    for src, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"  {src:20s} {count:5d}")

    print("\nBy content type:")
    for ct, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {ct:12s} {count:5d}")


if __name__ == "__main__":
    asyncio.run(main())
