"""
02_add_urls.py
Add a 'url' column to Sheet1-dedup.csv by prepending the dulox.cl base URL
to each product handle.

Input:  'Sheet1-dedup.csv'
Output: 'Sheet1-with-urls.csv'
"""

import pandas as pd

INPUT = "Sheet1-dedup.csv"
OUTPUT = "Sheet1-with-urls.csv"
BASE_URL = "https://dulox.cl/products/"

df = pd.read_csv(INPUT)

df["url"] = BASE_URL + df["Product: Handle"].str.strip()

df.to_csv(OUTPUT, index=False)

print(f"Added 'url' column to {len(df)} rows.")
print(f"Sample URLs:")
for url in df["url"].head(5):
    print(f"  {url}")
print(f"Saved to: {OUTPUT}")
