"""
Agent 4: Image Generator
Together AI FLUX integration for generating campaign visuals.
"""

import base64
import requests
import concurrent.futures


def generate_image(
    prompt: str,
    api_key: str,
    width: int = 1024,
    height: int = 1024,
) -> tuple[bytes | None, str | None]:
    """
    Generate one image via Together AI FLUX.1-schnell.

    Returns:
        (image_bytes, error_message) — image_bytes is None on failure.
    """
    try:
        resp = requests.post(
            "https://api.together.xyz/v1/images/generations",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "black-forest-labs/FLUX.1-schnell",
                "prompt": prompt,
                "width": width,
                "height": height,
                "steps": 4,
                "n": 1,
                "response_format": "b64_json",
            },
            timeout=60,
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


def generate_carousel_image(prompt: str, api_key: str) -> tuple[bytes | None, str | None]:
    """Generate a square carousel image (1080x1080 → 1024x1024 for FLUX)."""
    return generate_image(prompt, api_key, width=1024, height=1024)


def generate_reel_image(prompt: str, api_key: str) -> tuple[bytes | None, str | None]:
    """Generate a portrait reel frame (1080x1920 → 768x1344 for FLUX)."""
    return generate_image(prompt, api_key, width=768, height=1344)


def generate_batch(
    prompts: list[dict],
    api_key: str,
    progress_callback=None,
) -> list[dict]:
    """
    Generate multiple images in parallel.

    Args:
        prompts: list of {"label": str, "prompt": str, "format": "carousel"|"reel"}
        api_key: Together AI key
        progress_callback: fn(done, total) called after each image completes

    Returns:
        list of {"label": str, "prompt": str, "image": bytes|None, "error": str|None}
    """
    results = [None] * len(prompts)

    def _gen(idx):
        item = prompts[idx]
        if item["format"] == "reel":
            img, err = generate_reel_image(item["prompt"], api_key)
        else:
            img, err = generate_carousel_image(item["prompt"], api_key)
        return idx, img, err

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
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
        r"(?:Image generation prompt|FLUX prompt|Image prompt|Visual prompt|Generation prompt)[:\s]*(.+?)(?=\n\n|\n\*\*|\n#{1,3} |\Z)",
        r"\*\*(?:Image generation prompt|FLUX prompt)\*\*[:\s]*(.+?)(?=\n\n|\n\*\*|\n#{1,3} |\Z)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, campaign_text, re.IGNORECASE | re.DOTALL)
        for m in matches:
            cleaned = m.strip().strip('"').strip("*").strip()
            if len(cleaned) > 30:  # Only meaningful prompts
                prompts.append(cleaned)

    # Determine format based on context — check if prompt is near "reel" or "carousel" heading
    result = []
    for i, prompt in enumerate(prompts):
        # Simple heuristic: first 4 are carousel, rest are reel
        label = f"Visual {i+1}"
        fmt = "carousel"

        # Check if prompt text hints at reel
        lower = prompt.lower()
        if any(w in lower for w in ["vertical", "portrait", "reel", "9:16", "story"]):
            fmt = "reel"

        result.append({
            "label": label,
            "prompt": prompt,
            "format": fmt,
        })

    return result[:10]  # Cap at 10 images
