"""
fetch_images.py — Bulk Shopify image URL fetcher
================================================
Fetches the og:image or og:image:secure_url from each product page
and saves it to products.image_url in the database.

Run:
    python scripts/fetch_images.py          # fetch missing only
    python scripts/fetch_images.py --all    # re-fetch all (overwrites)
    python scripts/fetch_images.py --dry    # print what would be fetched, no writes
"""

import re
import sys
import time
import sqlite3
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB   = ROOT / "dataset" / "products.db"

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def fetch_image_url(url: str) -> str | None:
    """Fetch the CDN image URL from a Shopify product page."""
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=10, headers=HEADERS)
        resp.raise_for_status()
        text = resp.text

        # Try secure_url first (always https)
        m = re.search(
            r'<meta[^>]+property=["\']og:image:secure_url["\'][^>]+content=["\'](https://[^"\']+)["\']',
            text
        )
        if not m:
            m = re.search(
                r'<meta[^>]+content=["\'](https://[^"\']+)["\'][^>]+property=["\']og:image:secure_url["\']',
                text
            )
        # Fall back to og:image (may be http or https)
        if not m:
            m = re.search(
                r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https?://[^"\']+)["\']',
                text
            )
        if not m:
            m = re.search(
                r'<meta[^>]+content=["\'](https?://[^"\']+)["\'][^>]+property=["\']og:image["\']',
                text
            )
        if m:
            # Strip query params (v= version string) to get clean CDN path
            img = m.group(1).split("?")[0]
            # Force https
            img = img.replace("http://", "https://", 1)
            return img
        return None
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}")
        return None


def main():
    refetch_all = "--all" in sys.argv
    dry_run     = "--dry" in sys.argv

    conn = sqlite3.connect(DB, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if refetch_all:
        cur.execute("SELECT handle, url FROM products WHERE url IS NOT NULL AND url != ''")
    else:
        cur.execute("SELECT handle, url FROM products WHERE url IS NOT NULL AND url != '' AND (image_url IS NULL OR image_url = '')")

    rows = cur.fetchall()
    total = len(rows)
    print(f"{'[DRY RUN] ' if dry_run else ''}Fetching images for {total} products...")

    ok = 0
    failed = 0
    for i, row in enumerate(rows, 1):
        handle = row["handle"]
        url    = row["url"]
        print(f"  [{i}/{total}] {handle} ...", end=" ", flush=True)

        img = fetch_image_url(url)
        if img:
            print(f"OK — {img[:60]}...")
            ok += 1
            if not dry_run:
                for attempt in range(5):
                    try:
                        cur.execute("UPDATE products SET image_url = ? WHERE handle = ?",
                                    (img, handle))
                        break
                    except sqlite3.OperationalError:
                        time.sleep(1 + attempt)
        else:
            print("no image found")
            failed += 1

        # Polite delay — don't hammer the server
        if i < total:
            time.sleep(0.3)

    if not dry_run:
        for attempt in range(10):
            try:
                conn.commit()
                break
            except sqlite3.OperationalError:
                time.sleep(2)
        print(f"\nDone: {ok} saved, {failed} not found. DB updated.")
    else:
        print(f"\nDry run complete: {ok} would be saved, {failed} not found.")

    conn.close()


if __name__ == "__main__":
    main()
