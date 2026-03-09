"""
Agent 2: Product Scraper Agent
Scrapes Neeman's website for real product data via Shopify JSON API.
Prioritises bestsellers and premium articles.
"""

import re
import requests
import streamlit as st

# ── Verified bestseller handles (scraped & confirmed on neemans.com) ──
BESTSELLER_HANDLES = [
    "crossover-brogues",
    "sole-max-slip-ons-ultra-beige",
    "sole-max-cush-slip-ons-for-men-beige",
    "begin-walk-glide-black",
    "knit-gliders-black",
    "knit-gliders-for-men-beige",
    "begin-walk-breeze-black",
    "begin-walk-lite-for-men-black",
    "urban-casuals",
    "the-minimals",
    "purewhoosh-breeze",
    "purewhoosh-flow-black",
    "purewhoosh-duo-glides-black",
    "lush-glider-for-men-beige",
    "begin-walk-all-day-for-men-black",
    "begin-walk-pro",
    "begin-walk-ease-for-men",
    "begin-walk-flow",
    "begin-walk-anchor-black",
    "begin-walk-pulse-for-men",
]

# Hardcoded fallback products matching real bestsellers
FALLBACK_PRODUCTS = [
    {"name": "Crossover Brogues", "category": "Formal", "price": 4495, "material": "Premium Knit", "image_url": None, "url": "https://neemans.com/products/crossover-brogues", "is_bestseller": True},
    {"name": "Sole Max Slip Ons", "category": "Slip Ons", "price": 3495, "material": "Recycled Knit + Max Cushion Sole", "image_url": None, "url": "https://neemans.com/products/sole-max-slip-ons-ultra-beige", "is_bestseller": True},
    {"name": "Begin Walk Glide", "category": "Sneakers", "price": 3295, "material": "Recycled Knit", "image_url": None, "url": "https://neemans.com/products/begin-walk-glide-black", "is_bestseller": True},
    {"name": "Knit Gliders", "category": "Sneakers", "price": 2999, "material": "Recycled Knit", "image_url": None, "url": "https://neemans.com/products/knit-gliders-black", "is_bestseller": True},
    {"name": "Begin Walk Breeze", "category": "Sneakers", "price": 2599, "material": "Breathable Knit Mesh", "image_url": None, "url": "https://neemans.com/products/begin-walk-breeze-black", "is_bestseller": True},
    {"name": "Begin Walk Lite", "category": "Sneakers", "price": 2499, "material": "Lightweight Recycled Knit", "image_url": None, "url": "https://neemans.com/products/begin-walk-lite-for-men-black", "is_bestseller": True},
    {"name": "Urban Casuals", "category": "Casual", "price": 3295, "material": "Premium Sustainable", "image_url": None, "url": "https://neemans.com/products/urban-casuals", "is_bestseller": True},
    {"name": "The Minimals", "category": "Sneakers", "price": 2799, "material": "Minimalist Knit", "image_url": None, "url": "https://neemans.com/products/the-minimals", "is_bestseller": True},
    {"name": "PureWhoosh Breeze", "category": "Sneakers", "price": 3495, "material": "PureWhoosh Tech", "image_url": None, "url": "https://neemans.com/products/purewhoosh-breeze", "is_bestseller": True},
    {"name": "Lush Glider", "category": "Sneakers", "price": 3295, "material": "Premium Knit + Cushion Sole", "image_url": None, "url": "https://neemans.com/products/lush-glider-for-men-beige", "is_bestseller": True},
    {"name": "Begin Walk All Day", "category": "Sneakers", "price": 2999, "material": "Recycled Knit + ReLive Sole", "image_url": None, "url": "https://neemans.com/products/begin-walk-all-day-for-men-black", "is_bestseller": True},
    {"name": "Begin Walk Pro", "category": "Sneakers", "price": 3495, "material": "Premium Recycled Knit", "image_url": None, "url": "https://neemans.com/products/begin-walk-pro", "is_bestseller": True},
]


def _fetch_collection_json(collection: str = "all", page: int = 1) -> list[dict]:
    """Fetch products from a Neeman's collection via Shopify JSON API."""
    try:
        url = f"https://neemans.com/collections/{collection}/products.json?page={page}&limit=30"
        r = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "NeemansLaunchAgent/1.0"},
        )
        if r.status_code == 200:
            return r.json().get("products", [])
    except Exception:
        pass
    return []


def _fetch_product_by_handle(handle: str) -> dict | None:
    """Fetch a single product by its Shopify handle."""
    try:
        url = f"https://neemans.com/products/{handle}.json"
        r = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "NeemansLaunchAgent/1.0"},
        )
        if r.status_code == 200:
            return r.json().get("product")
    except Exception:
        pass
    return None


def _parse_product(p: dict, is_bestseller: bool = False) -> dict:
    """Parse a Shopify product JSON into a clean dict."""
    variants = p.get("variants", [])
    prices = [float(v["price"]) for v in variants if v.get("price")]
    images = [img["src"] for img in p.get("images", [])[:3]]

    # Get availability
    available_sizes = sorted(
        {v.get("option1", "") for v in variants if v.get("available")},
        key=lambda s: float(s) if s.replace(".", "").isdigit() else 0,
    )

    # Infer material from tags or description
    body = re.sub(r"<[^>]+>", " ", p.get("body_html", ""))
    body = re.sub(r"\s+", " ", body).strip()[:300]

    material = "Premium Sustainable"
    body_lower = body.lower()
    if "merino" in body_lower or "wool" in body_lower:
        material = "Merino Wool"
    elif "hemp" in body_lower:
        material = "Hemp Canvas"
    elif "recycled" in body_lower or "pet" in body_lower:
        material = "Recycled PET"
    elif "knit" in body_lower:
        material = "Recycled Knit"
    elif "purewhoosh" in body_lower or "whoosh" in body_lower:
        material = "PureWhoosh Tech"

    return {
        "name": p.get("title", ""),
        "category": p.get("product_type", "Footwear"),
        "price": int(min(prices)) if prices else 0,
        "material": material,
        "image_url": images[0] if images else None,
        "all_images": images,
        "url": f"https://neemans.com/products/{p.get('handle', '')}",
        "handle": p.get("handle", ""),
        "available_sizes": available_sizes,
        "description": body[:200],
        "is_bestseller": is_bestseller,
    }


@st.cache_data(ttl=3600, show_spinner=False)
def scrape_products() -> tuple[list[dict], bool]:
    """
    Scrape Neeman's products — bestsellers first, then collections.

    Returns:
        (products_list, is_live) — is_live=True if scraped, False if fallback.
    """
    all_products = {}  # keyed by handle to deduplicate
    bestseller_order = []  # preserve bestseller ordering

    # ── Phase 1: Fetch bestsellers individually ──
    for handle in BESTSELLER_HANDLES:
        try:
            raw = _fetch_product_by_handle(handle)
            if raw:
                parsed = _parse_product(raw, is_bestseller=True)
                if parsed["name"] and parsed["price"] > 0:
                    h = raw.get("handle", handle)
                    all_products[h] = parsed
                    bestseller_order.append(h)
        except Exception:
            continue

    # ── Phase 2: Fetch from collections ──
    collections = ["best-selling", "best-sellers", "all", "mens", "womens", "new-arrivals"]

    for coll in collections:
        try:
            raw_list = _fetch_collection_json(coll)
            for p in raw_list:
                handle = p.get("handle", "")
                if handle and handle not in all_products:
                    parsed = _parse_product(p)
                    if parsed["name"] and parsed["price"] > 0:
                        all_products[handle] = parsed
        except Exception:
            continue

    if all_products:
        # Bestsellers first (in order), then rest sorted by price desc
        result = []
        seen = set()

        # Add bestsellers in order
        for h in bestseller_order:
            if h in all_products and h not in seen:
                result.append(all_products[h])
                seen.add(h)

        # Add remaining sorted by price
        remaining = [
            all_products[h] for h in all_products
            if h not in seen
        ]
        remaining.sort(key=lambda x: x["price"], reverse=True)
        result.extend(remaining)

        return result[:25], True

    # Fallback
    return FALLBACK_PRODUCTS, False


def products_to_prompt_text(products: list[dict]) -> str:
    """Format selected products as text for Claude's prompt."""
    lines = ["## Products Available for Campaign\n"]
    for i, p in enumerate(products, 1):
        badge = " ⭐ BESTSELLER" if p.get("is_bestseller") else ""
        lines.append(f"**{i}. {p['name']}**{badge}")
        lines.append(f"   - Category: {p['category']}")
        lines.append(f"   - Price: ₹{p['price']:,}")
        lines.append(f"   - Material: {p['material']}")
        if p.get("url"):
            lines.append(f"   - URL: {p['url']}")
        if p.get("image_url"):
            lines.append(f"   - Product Image: {p['image_url']}")
        if p.get("description"):
            lines.append(f"   - Description: {p['description']}")
        lines.append("")
    return "\n".join(lines)
