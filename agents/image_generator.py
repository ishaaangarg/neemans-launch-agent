"""
Agent 4: Image Generator
Together AI FLUX integration for generating campaign visuals.
Supports two modes:
  - Pro (FLUX1.1 Pro): high-quality text-to-image (~$0.50 per batch of 10)
  - Shoe+ (FLUX.1-kontext-pro): image-to-image with real Neeman's shoe in scene
"""

import base64
import requests
import concurrent.futures

try:
    from together import Together
    HAS_SDK = True
except ImportError:
    HAS_SDK = False


# ── Visual mode configs ──
VISUAL_MODELS = {
    "quick": {
        "model": "black-forest-labs/FLUX1.1-pro",
        "steps": 25,
        "label": "FLUX 1.1 Pro",
        "supports_image_ref": False,
    },
    "shoe_plus": {
        "model": "black-forest-labs/FLUX.1-kontext-pro",
        "steps": 28,
        "label": "Flux Kontext Pro",
        "supports_image_ref": True,
    },
}


def generate_image(
    prompt: str,
    api_key: str,
    mode: str = "quick",
    width: int = 1024,
    height: int = 1024,
    ref_image_url: str | None = None,
) -> tuple[bytes | None, str | None]:
    """
    Generate one image via Together AI.

    Returns:
        (image_bytes, error_message) — image_bytes is None on failure.
    """
    cfg = VISUAL_MODELS.get(mode, VISUAL_MODELS["quick"])

    # ── SDK path (preferred) ──
    if HAS_SDK:
        try:
            client = Together(api_key=api_key)
            kwargs = dict(
                model=cfg["model"],
                prompt=prompt,
                width=width,
                height=height,
                steps=cfg["steps"],
                n=1,
                response_format="b64_json",
            )
            # Kontext: pass the product shoe as reference image
            if cfg["supports_image_ref"] and ref_image_url:
                kwargs["image_url"] = ref_image_url

            resp = client.images.generate(**kwargs)

            if resp.data and resp.data[0].b64_json:
                return base64.b64decode(resp.data[0].b64_json), None
            # Fallback: if URL is returned instead
            if resp.data and hasattr(resp.data[0], "url") and resp.data[0].url:
                img_resp = requests.get(resp.data[0].url, timeout=30)
                if img_resp.status_code == 200:
                    return img_resp.content, None
            return None, "No image data in response"
        except Exception as e:
            return None, str(e)

    # ── Fallback: raw REST API (no SDK) ──
    try:
        payload = {
            "model": cfg["model"],
            "prompt": prompt,
            "width": width,
            "height": height,
            "steps": cfg["steps"],
            "n": 1,
            "response_format": "b64_json",
        }
        if cfg["supports_image_ref"] and ref_image_url:
            payload["image_url"] = ref_image_url

        resp = requests.post(
            "https://api.together.xyz/v1/images/generations",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=90,
        )

        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}: {resp.text[:200]}"

        data = resp.json()
        if data.get("data") and data["data"][0].get("b64_json"):
            img_b64 = data["data"][0]["b64_json"]
            return base64.b64decode(img_b64), None

        # Fallback to URL
        if data.get("data") and data["data"][0].get("url"):
            img_resp = requests.get(data["data"][0]["url"], timeout=30)
            if img_resp.status_code == 200:
                return img_resp.content, None

        return None, "No image data in response"

    except Exception as e:
        return None, str(e)


def generate_carousel_image(
    prompt: str,
    api_key: str,
    mode: str = "quick",
    ref_image_url: str | None = None,
) -> tuple[bytes | None, str | None]:
    """Generate a square carousel image (1024x1024)."""
    return generate_image(prompt, api_key, mode, 1024, 1024, ref_image_url)


def generate_reel_image(
    prompt: str,
    api_key: str,
    mode: str = "quick",
    ref_image_url: str | None = None,
) -> tuple[bytes | None, str | None]:
    """Generate a portrait reel frame (768x1344)."""
    return generate_image(prompt, api_key, mode, 768, 1344, ref_image_url)


def generate_batch(
    prompts: list[dict],
    api_key: str,
    mode: str = "quick",
    ref_image_url: str | None = None,
    progress_callback=None,
) -> list[dict]:
    """
    Generate multiple images in parallel.

    Args:
        prompts: list of {"label": str, "prompt": str, "format": "carousel"|"reel"}
        api_key: Together AI key
        mode: "quick" or "shoe_plus"
        ref_image_url: product image URL for shoe_plus mode
        progress_callback: fn(done, total) called after each image completes

    Returns:
        list of {"label": str, "prompt": str, "image": bytes|None, "error": str|None}
    """
    results = [None] * len(prompts)

    # Quality prefix for Pro mode
    QUALITY_PREFIX = (
        "Ultra-high-quality professional advertising photograph, "
        "shot on Canon EOS R5 with 85mm f/1.4 lens, "
        "studio-grade lighting, sharp focus, commercial product photography, "
        "clean modern aesthetic, premium brand feel. "
    )

    def _gen(idx):
        item = prompts[idx]
        prompt = item["prompt"]

        # For shoe_plus mode: prepend instruction for Kontext
        if mode == "shoe_plus" and ref_image_url:
            prompt = f"Place this Neeman's shoe in the following scene: {prompt}"
        elif mode == "quick":
            # Add quality prefix for Pro mode text-to-image
            prompt = f"{QUALITY_PREFIX}{prompt}"

        if item["format"] == "reel":
            img, err = generate_reel_image(prompt, api_key, mode, ref_image_url)
        else:
            img, err = generate_carousel_image(prompt, api_key, mode, ref_image_url)
        return idx, img, err

    # Fewer workers for heavier Kontext model
    max_w = 3 if mode == "shoe_plus" else 5

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_w) as executor:
        futures = {executor.submit(_gen, i): i for i in range(len(prompts))}
        done_count = 0
        for future in concurrent.futures.as_completed(futures):
            try:
                idx, img, err = future.result()
                results[idx] = {
                    "label": prompts[idx]["label"],
                    "prompt": prompts[idx]["prompt"],
                    "format": prompts[idx]["format"],
                    "image": img,
                    "error": err,
                }
            except Exception as e:
                idx = futures[future]
                results[idx] = {
                    "label": prompts[idx]["label"],
                    "prompt": prompts[idx]["prompt"],
                    "format": prompts[idx]["format"],
                    "image": None,
                    "error": str(e),
                }
            done_count += 1
            if progress_callback:
                progress_callback(done_count, len(prompts))

    return results


def extract_image_prompts_from_campaign(campaign_text: str) -> list[dict]:
    """
    Extract image generation prompts from the campaign output.
    Looks for patterns like "Image generation prompt:" or "FLUX prompt:" in the text.
    """
    import re

    prompts = []
    # Match various prompt label patterns
    patterns = [
        r"(?:Image generation prompt|FLUX prompt|Image prompt|Visual prompt|Generation prompt)[:\s]*(.+?)(?=\n\n|\n\*\*|\n#{1,3} |\n-\s|\Z)",
        r"\*\*(?:Image generation prompt|FLUX prompt)\*\*[:\s]*(.+?)(?=\n\n|\n\*\*|\n#{1,3} |\n-\s|\Z)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, campaign_text, re.IGNORECASE | re.DOTALL)
        for m in matches:
            cleaned = m.strip().strip('"').strip("*").strip()
            if len(cleaned) > 30:  # Only meaningful prompts
                # Avoid duplicates
                if cleaned not in [p for p in prompts]:
                    prompts.append(cleaned)

    # Determine format based on context
    result = []
    # Find section boundaries to determine carousel vs reel
    for i, prompt in enumerate(prompts):
        label = f"Visual {i+1}"
        fmt = "carousel"

        # Check if prompt text hints at reel/portrait
        lower = prompt.lower()
        if any(w in lower for w in ["vertical", "portrait", "reel", "9:16", "story", "scene"]):
            fmt = "reel"

        result.append({
            "label": label,
            "prompt": prompt,
            "format": fmt,
        })

    return result[:12]  # Cap at 12 images
