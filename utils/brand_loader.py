"""
Brand context loader — scans working directory for brand files at startup.
Falls back to hardcoded brand DNA if no files found.
"""

import os
import re
from brand.context import BRAND_DNA


def _sanitize(text: str) -> str:
    """Strip potential prompt injection patterns from loaded files."""
    # Remove common injection attempts
    patterns = [
        r"(?i)ignore (?:all )?(?:previous |above )?instructions",
        r"(?i)you are now",
        r"(?i)system:\s*",
        r"(?i)new instructions:",
    ]
    cleaned = text
    for p in patterns:
        cleaned = re.sub(p, "[FILTERED]", cleaned)
    return cleaned


def load_brand_context(search_dirs: list[str] | None = None) -> tuple[str, list[str]]:
    """
    Load brand context from markdown/text files in the working directory.

    Returns:
        (combined_context: str, loaded_files: list of filenames that were loaded)
    """
    if search_dirs is None:
        search_dirs = [
            os.getcwd(),
            os.path.dirname(os.path.abspath(__file__)),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
        ]

    # Priority filenames to look for
    priority_names = [
        "neemans_brand.md",
        "brand_context.md",
        "claude.md",
        "brand_guidelines.md",
        "CLAUDE.md",
    ]

    loaded_files = []
    chunks = []

    # First pass: load priority files
    seen_paths = set()
    for name in priority_names:
        for base in search_dirs:
            path = os.path.join(base, name)
            real = os.path.realpath(path)
            if real in seen_paths:
                continue
            if os.path.isfile(path):
                try:
                    with open(path, encoding="utf-8") as f:
                        content = f.read()
                    if content.strip():
                        chunks.append(f"--- {name} ---\n{_sanitize(content)}")
                        loaded_files.append(name)
                        seen_paths.add(real)
                except Exception:
                    pass

    # Second pass: scan for any other .md or .txt files
    for base in search_dirs:
        if not os.path.isdir(base):
            continue
        try:
            for fname in sorted(os.listdir(base)):
                if not fname.endswith((".md", ".txt")):
                    continue
                if fname.lower() in ("readme.md", "setup.md", "requirements.txt"):
                    continue
                path = os.path.join(base, fname)
                real = os.path.realpath(path)
                if real in seen_paths:
                    continue
                if os.path.isfile(path):
                    try:
                        with open(path, encoding="utf-8") as f:
                            content = f.read()
                        if content.strip() and len(content) > 100:
                            chunks.append(f"--- {fname} ---\n{_sanitize(content)}")
                            loaded_files.append(fname)
                            seen_paths.add(real)
                    except Exception:
                        pass
        except Exception:
            pass

    if chunks:
        combined = "\n\n".join(chunks)
        # Cap at 40K chars to stay within context limits
        if len(combined) > 40000:
            combined = combined[:40000] + "\n\n[...truncated for length]"
        return combined, loaded_files

    # Fallback to hardcoded brand DNA
    return BRAND_DNA, ["(built-in brand DNA)"]
