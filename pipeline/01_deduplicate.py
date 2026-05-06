"""
01_deduplicate.py
Remove duplicate rows from Sheet1 based on 'Product: Handle'.
Keeps the first occurrence of each unique handle.

Input:  'Productos-Categorizados - Sheet1.csv'
Output: 'Sheet1-dedup.csv'
"""

import pandas as pd
import os

INPUT = "Productos-Categorizados - Sheet1.csv"
OUTPUT = "Sheet1-dedup.csv"

df = pd.read_csv(INPUT)

rows_before = len(df)

# Remove rows where Product: Handle is empty/NaN
df = df[df["Product: Handle"].notna() & (df["Product: Handle"].str.strip() != "")]

# Deduplicate keeping first occurrence
df_dedup = df.drop_duplicates(subset=["Product: Handle"], keep="first")

rows_after = len(df_dedup)
rows_removed = rows_before - rows_after

df_dedup.to_csv(OUTPUT, index=False)

print(f"Input rows : {rows_before}")
print(f"Output rows: {rows_after}")
print(f"Removed    : {rows_removed} duplicates")
print(f"Saved to   : {OUTPUT}")
