"""
db.py — Supabase client abstraction layer for Dulox pricing app.

All reads/writes go through this module.  Scripts import from here instead
of using sqlite3 directly, so the rest of the codebase stays clean.

Column name note: SQLite had G / D (uppercase). Supabase uses g_score / d_score
(Postgres lowercases bare identifiers). This module normalises both directions:
  - reads:  g_score/d_score → G/D in returned dicts
  - writes: G/D → g_score/d_score before upsert
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from functools import lru_cache

import streamlit as st
from supabase import Client, create_client

# ── Client ────────────────────────────────────────────────────────────────────

def _get_client() -> Client:
    """Return a Supabase client, preferring st.secrets then env vars."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_SERVICE_ROLE"]
    except Exception:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_ROLE", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE not configured.")
    return create_client(url, key)


# Cache at session level — recreated once per Streamlit session
@st.cache_resource
def get_sb() -> Client:
    return _get_client()


# ── PROCESS_RULES ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_rules() -> dict:
    """Load PROCESS_RULES.json from app_settings table."""
    try:
        r = get_sb().table("app_settings").select("value").eq("key", "process_rules").single().execute()
        return r.data["value"] if r.data else {}
    except Exception:
        return {}


def _sanitize_nan(obj):
    """Recursively replace NaN/Inf floats with None so JSON serialization doesn't crash."""
    if isinstance(obj, float):
        return None if (obj != obj or obj == float('inf') or obj == float('-inf')) else obj
    if isinstance(obj, dict):
        return {k: _sanitize_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_nan(v) for v in obj]
    return obj


def save_rules(rules: dict) -> None:
    """Persist updated rules to app_settings and bust cache."""
    clean = _sanitize_nan(rules)
    get_sb().table("app_settings").upsert({"key": "process_rules", "value": clean}).execute()
    load_rules.clear()


# ── Products ──────────────────────────────────────────────────────────────────

def _from_sb(row: dict) -> dict:
    """Normalise Supabase row: g_score/d_score → G/D."""
    row = dict(row)
    row["G"] = row.pop("g_score", None)
    row["D"] = row.pop("d_score", None)
    return row


def _to_sb(product: dict) -> dict:
    """Normalise for upsert: G/D → g_score/d_score, strip None id."""
    row = dict(product)
    if "G" in row:
        row["g_score"] = row.pop("G")
    if "D" in row:
        row["d_score"] = row.pop("D")
    row.pop("id", None)  # let Postgres assign
    return row


@st.cache_data(ttl=30)
def load_all_products() -> list[dict]:
    """Return all products as a list of dicts (with G/D keys)."""
    r = get_sb().table("products").select("*").order("handle").execute()
    return [_from_sb(row) for row in (r.data or [])]


def load_profile_products(profile_key: str) -> list[dict]:
    """Return products for a single perfil_proceso."""
    r = (get_sb().table("products")
         .select("*")
         .eq("perfil_proceso", profile_key)
         .order("handle")
         .execute())
    return [_from_sb(row) for row in (r.data or [])]


def search_products(query: str, limit: int = 50) -> list[dict]:
    """Full-text-ish search on handle + descripcion_web."""
    sb = get_sb()
    # PostgREST ilike filter — two separate queries OR-ed
    r1 = sb.table("products").select("handle,descripcion_web,perfil_proceso,complejidad,g_score,d_score,dim_l_mm,dim_w_mm,dim_h_mm,dim_espesor_mm,image_url,bom_materials,bom_consumables,is_anchor").ilike("handle", f"%{query}%").limit(limit).execute()
    r2 = sb.table("products").select("handle,descripcion_web,perfil_proceso,complejidad,g_score,d_score,dim_l_mm,dim_w_mm,dim_h_mm,dim_espesor_mm,image_url,bom_materials,bom_consumables,is_anchor").ilike("descripcion_web", f"%{query}%").limit(limit).execute()
    seen = {}
    for row in (r1.data or []) + (r2.data or []):
        seen[row["handle"]] = _from_sb(row)
    return list(seen.values())[:limit]


def get_product(handle: str) -> dict | None:
    """Fetch a single product by handle."""
    r = get_sb().table("products").select("*").eq("handle", handle).limit(1).execute()
    return _from_sb(r.data[0]) if r.data else None


def handle_exists(handle: str) -> bool:
    r = get_sb().table("products").select("handle").eq("handle", handle).limit(1).execute()
    return bool(r.data)


def save_product(product: dict) -> tuple[bool, str]:
    """Upsert a single product. Returns (ok, message)."""
    try:
        row = _to_sb(product)
        get_sb().table("products").upsert(row, on_conflict="handle").execute()
        load_all_products.clear()
        return True, f"✅ `{product['handle']}` guardado."
    except Exception as e:
        return False, f"Error DB: {e}"


def save_product_batch(updates: list[dict]) -> None:
    """
    Batch-update c_value + x_flags for a list of {handle, c_value, x_flags}.
    x_flags may be a list — serialised to JSON string here.
    """
    sb = get_sb()
    for u in updates:
        x = u.get("x_flags", [])
        sb.table("products").update({
            "c_value": u.get("c_value"),
            "x_flags": json.dumps(x) if isinstance(x, list) else x,
        }).eq("handle", u["handle"]).execute()
    load_all_products.clear()


def save_bom(handle: str, mat_rows: list, cons_rows: list) -> None:
    """Persist BOM materials + consumables for a product."""
    get_sb().table("products").update({
        "bom_materials":   json.dumps(mat_rows,  ensure_ascii=False),
        "bom_consumables": json.dumps(cons_rows, ensure_ascii=False),
    }).eq("handle", handle).execute()
    load_all_products.clear()


def save_anchor(handle: str, profile_key: str, complejidad: str, rules: dict) -> None:
    """Mark handle as anchor for profile+complejidad; update PROCESS_RULES."""
    # Clear previous anchor for this slot
    get_sb().table("products").update({"is_anchor": 0}).eq("perfil_proceso", profile_key).eq("complejidad", complejidad).execute()
    # Set new anchor
    get_sb().table("products").update({"is_anchor": 1}).eq("handle", handle).execute()
    # Update rules
    if "profiles" in rules and profile_key in rules["profiles"]:
        anchors = rules["profiles"][profile_key].setdefault("anchors", {})
        anchors[complejidad] = handle
        save_rules(rules)
    load_all_products.clear()


# ── Categorization history ─────────────────────────────────────────────────────

def log_change(handle: str, old_perfil: str | None, new_perfil: str,
               old_comp: str | None, new_comp: str, reason: str,
               changed_by: str = "app") -> None:
    get_sb().table("categorization_history").insert({
        "handle":          handle,
        "old_perfil":      old_perfil,
        "new_perfil":      new_perfil,
        "old_complejidad": old_comp,
        "new_complejidad": new_comp,
        "reason":          reason,
        "changed_by":      changed_by,
        "changed_at":      datetime.now().isoformat(),
    }).execute()
