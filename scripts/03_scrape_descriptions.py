"""
03_scrape_descriptions.py
Scrape product descriptions from dulox.cl for each product in Sheet1-with-urls.csv.
Saves progress to a checkpoint file so runs can be resumed.

Input:  'Sheet1-with-urls.csv'
Output: 'Sheet1-scraped.csv'  (adds columns: descripcion_web, scrape_status)
        'scrape_checkpoint.json' (resume-safe progress tracker)
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import time
import os
import sys

INPUT = "Sheet1-with-urls.csv"
OUTPUT = "Sheet1-scraped.csv"
CHECKPOINT = "scrape_checkpoint.json"
DELAY = 1.5       # seconds between requests
TIMEOUT = 12      # seconds per request
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
}


def extract_description(html: str) -> str:
    """Extract product description text from dulox.cl Shopify HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # 1. Try the full description block inside tab-popup-content
    popup = soup.find(class_="tab-popup-content")
    if popup:
        text = popup.get_text(separator=" ", strip=True)
        if len(text) > 30:
            return text[:2000]

    # 2. Try meta description (always present, clean specs text)
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"].strip()

    # 3. Fallback: page title
    title = soup.find("title")
    if title:
        return title.get_text(strip=True)

    return ""


def scrape_url(url: str) -> tuple[str, str]:
    """
    Returns (description_text, status)
    status: 'ok' | '404' | 'timeout' | 'error'
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 404:
            return "", "404"
        if resp.status_code != 200:
            return "", f"http_{resp.status_code}"
        description = extract_description(resp.text)
        return description, "ok"
    except requests.Timeout:
        return "", "timeout"
    except Exception as e:
        return "", f"error: {str(e)[:80]}"


def load_checkpoint() -> dict:
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT) as f:
            return json.load(f)
    return {}


def save_checkpoint(checkpoint: dict):
    with open(CHECKPOINT, "w") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)


def main():
    df = pd.read_csv(INPUT)

    # Initialize columns if not present
    if "descripcion_web" not in df.columns:
        df["descripcion_web"] = ""
    if "scrape_status" not in df.columns:
        df["scrape_status"] = ""

    checkpoint = load_checkpoint()

    total = len(df)
    done = sum(1 for h in df["Product: Handle"] if str(h) in checkpoint)
    print(f"Total products: {total} | Already scraped: {done} | Remaining: {total - done}")

    for i, row in df.iterrows():
        handle = str(row["Product: Handle"]).strip()

        # Skip already processed
        if handle in checkpoint:
            df.at[i, "descripcion_web"] = checkpoint[handle]["description"]
            df.at[i, "scrape_status"] = checkpoint[handle]["status"]
            continue

        url = str(row["url"]).strip()
        description, status = scrape_url(url)

        df.at[i, "descripcion_web"] = description
        df.at[i, "scrape_status"] = status

        checkpoint[handle] = {"description": description, "status": status}

        # Print progress every 10 items
        completed = sum(1 for h in df["Product: Handle"].iloc[:i+1] if str(h) in checkpoint)
        if completed % 10 == 0 or i == total - 1:
            pct = completed / total * 100
            print(f"  [{completed}/{total}] {pct:.0f}%  last: {status} — {handle[:50]}")
            # Save checkpoint and partial CSV periodically
            save_checkpoint(checkpoint)
            df.to_csv(OUTPUT, index=False)

        if status == "ok":
            time.sleep(DELAY)
        else:
            time.sleep(0.3)  # shorter delay on errors

    # Final save
    save_checkpoint(checkpoint)
    df.to_csv(OUTPUT, index=False)

    # Summary
    counts = df["scrape_status"].value_counts()
    print("\n=== Scrape Summary ===")
    print(counts.to_string())
    print(f"\nSaved to: {OUTPUT}")


if __name__ == "__main__":
    main()
