"""
Agent 2: Product Scraper Agent
Scrapes Neeman's website for real product data via Shopify JSON API.
"""

import re
import requests
import streamlit as st

# Hardcoded fallback products (real Neeman's categories)
FALLBACK_PRODUCTS = [
    {"name": "Begin Walk All Day", "category": "Sneakers", "price": 2999, "material": "Recycled Knit + ReLive Sole", "image_url": None, "url": "https://neemans.com/collections/sneakers"},
    {"name": "Neo Runners", "category": "Sneakers", "price": 3495, "material": "Recycled PET + Merino", "image_url": None, "url": "https://neemans.com/collections/sneakers"},
    {"name": "Woollen Loafers", "category": "Loafers", "price": 3995, "material": "Merino Wool", "image_url": None, "url": "https://neemans.com/collections/loafers"},
    {"name": "Hemp Sneakers", "category": "Sneakers", "price": 3295, "material": "Hemp Canvas", "image_url": None, "url": "https://neemans.com/collections/sneakers"},
    {"name": "Classic Flip Flops", "category": "Flip Flops", "price": 1995, "material": "Natural Rubber + Recycled Straps", "image_url": None, "url": "https://neemans.com/collections/flip-flops"},
    {"name": "Work Loafers", "category": "Formal", "price": 4495, "material": "Vegan Leather", "image_url": None, "url": "https://neemans.com/collections/loafers"},
    {"name": "Wool Joggers", "category": "Running", "price": 3995, "material": "Merino Wool Blend", "image_url": None, "url": "https://neemans.com/collections/sneakers"},
    {"name": "Women's Ballet Flats", "category": "Women's", "price": 2995, "material": "Hemp + Wool", "image_url": None, "url": "https://neemans.com/collections/womens"},
    {"name": "Kids Sneakers", "category": "Kids", "price": 2495, "material": "Recycled Canvas", "image_url": None, "url": "https://neemans.com/collections/kids"},
    {"name": "Begin Walk Breeze", "category": "Sneakers", "price": 2599, "material": "Breathable Knit Mesh", "image_url": None, "url": "https://neemans.com/collections/sneakers"},
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


def _parse_product(p: dict) -> dict:
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
    }


@st.cache_data(ttl=3600, show_spinner=False)
def scrape_products() -> tuple[list[dict], bool]:
    """
    Scrape Neeman's products from multiple collections.

    Returns:
        (products_list, is_live) — is_live=True if scraped, False if fallback.
    """
    all_products = {}  # keyed by handle to deduplicate

    collections = ["all", "mens", "womens", "new-arrivals"]

    for coll in collections:
        try:
            raw = _fetch_collection_json(coll)
            for p in raw:
                handle = p.get("handle", "")
                if handle and handle not in all_products:
                    parsed = _parse_product(p)
                    if parsed["name"] and parsed["price"] > 0:
                        all_products[handle] = parsed
        except Exception:
            continue

    if all_products:
        # Sort by price descending, take top 20
        products = sorted(all_products.values(), key=lambda x: x["price"], reverse=True)[:20]
        return products, True

    # Fallback
    return FALLBACK_PRODUCTS, False


def products_to_prompt_text(products: list[dict]) -> str:
    """Format selected products as text for Claude's prompt."""
    lines = ["## Products Available for Campaign\n"]
    for i, p in enumerate(products, 1):
        lines.append(f"**{i}. {p['name']}**")
        lines.append(f"   - Category: {p['category']}")
        lines.append(f"   - Price: ₹{p['price']:,}")
        lines.append(f"   - Material: {p['material']}")
        if p.get("url"):
            lines.append(f"   - URL: {p['url']}")
        if p.get("description"):
            lines.append(f"   - Description: {p['description']}")
        lines.append("")
    return "\n".join(lines)
