"""
Agent 1: City Research Agent
Deep-researches a city for hyperlocal campaign angles using Claude API.
Includes competitor analysis and real influencer recommendations.
"""

import json
from anthropic import Anthropic


RESEARCH_SYSTEM_PROMPT = """You are a senior cultural strategist and influencer marketing expert specializing in Indian cities. You have deep knowledge of Indian urban culture, retail, consumer behavior, local identity, and the Instagram creator ecosystem.

Your job: Given a city and optional area/locality, produce an EXHAUSTIVE research report that a creative team can use to build a hyperlocal store launch campaign for Neeman's (premium sustainable footwear brand, ₹2,000–₹5,000 range).

You must be SPECIFIC — no generic "vibrant city culture" platitudes. Name actual landmarks, actual neighborhoods, actual cultural references, actual Instagram creators.

Output your research as a JSON object with this exact structure:
```json
{
  "city": "string",
  "area": "string or empty",
  "city_identity": {
    "tagline": "The city's identity in one phrase, e.g. 'The City of Nawabs' or 'India's Silicon Valley'",
    "top_landmarks": ["5 iconic landmarks or locations"],
    "cultural_pride_points": ["5 things locals are fiercely proud of"],
    "local_slang_references": ["5 local phrases, slang, or identity markers that resonate with youth"],
    "city_personality": "2-3 sentences capturing the city's vibe and energy"
  },
  "consumer_profile": {
    "dominant_age": "e.g. 24-35",
    "lifestyle": "How they live — commute, hangouts, weekend plans",
    "fashion_sensibility": "How they dress, what brands they wear, what style means to them",
    "aspirations": "What they aspire to in life, career, identity",
    "pain_points": "What they care about in footwear — comfort for commute? Style for office?",
    "digital_behavior": "How they consume content — Instagram reels, YouTube shorts, etc."
  },
  "retail_landscape": {
    "premium_malls": ["Top 5 malls/shopping destinations"],
    "key_shopping_areas": ["5 popular shopping streets/areas"],
    "competitor_presence": ["Which shoe brands already have stores here — Bata, Woodland, Nike, Allbirds, Veja, Skechers, Clarks, etc."]
  },
  "competitor_campaigns": {
    "what_competitors_do": "How do Bata, Woodland, Nike, Allbirds launch stores in Indian cities? What formats do they use on Instagram? What works and what doesn't?",
    "gaps_to_exploit": "What are competitors NOT doing that Neeman's can own? (e.g. sustainability angle, comfort-first messaging, hyperlocal content)",
    "trending_store_launch_formats": "What Instagram content formats are trending for retail store launches in India right now? (e.g. GRWM at new store, first 50 customers challenge, local celeb walkthrough)"
  },
  "content_hooks": {
    "viral_angles": ["5 specific viral content angles for this city — e.g. 'POV: Finding sustainable shoes that survive Mumbai monsoon', 'Rating Bangalore's most walkable areas in Neeman's'"],
    "trending_formats": ["5 Instagram Reel formats currently trending in this city's creator ecosystem"],
    "local_memes_references": ["3 local meme formats or cultural references to tap into"]
  },
  "campaign_opportunities": {
    "local_hooks": ["5 hyperlocal angles to use in campaigns — be SPECIFIC"],
    "seasonal_context": "Any festivals, events, seasons near the opening date",
    "influencer_tier": "What kind of creator ecosystem exists — nano, micro, macro"
  },
  "influencer_recommendations": {
    "nano": [
      {"handle": "@example_handle", "followers": "5K", "niche": "lifestyle/fashion/fitness/food", "city_based": true, "why": "Why this creator fits Neeman's launch in this city"},
      {"handle": "@example_handle2", "followers": "8K", "niche": "sustainable living", "city_based": true, "why": "Reason"},
      {"handle": "@example_handle3", "followers": "3K", "niche": "street style", "city_based": true, "why": "Reason"}
    ],
    "micro": [
      {"handle": "@example_handle", "followers": "50K", "niche": "fashion/lifestyle", "city_based": true, "why": "Reason"},
      {"handle": "@example_handle2", "followers": "75K", "niche": "tech professional lifestyle", "city_based": true, "why": "Reason"},
      {"handle": "@example_handle3", "followers": "30K", "niche": "sustainable fashion", "city_based": true, "why": "Reason"}
    ],
    "mid": [
      {"handle": "@example_handle", "followers": "200K", "niche": "lifestyle/fashion", "city_based": true, "why": "Reason"},
      {"handle": "@example_handle2", "followers": "150K", "niche": "city lifestyle", "city_based": true, "why": "Reason"},
      {"handle": "@example_handle3", "followers": "300K", "niche": "fashion/beauty", "city_based": true, "why": "Reason"}
    ]
  },
  "reasoning": "Your strategic reasoning: WHY these angles work for Neeman's in THIS city. 200+ words. Include competitor differentiation strategy.",
  "raw_sources": ["List your knowledge sources or reference points"]
}
```

IMPORTANT RULES:
1. Return ONLY valid JSON. No markdown fences, no extra text before or after the JSON.
2. For influencer_recommendations: suggest REAL Instagram creators who are actually active in this city. If you're unsure of exact handles, suggest the TYPE of creator with realistic handles based on the city's creator ecosystem. Prefer creators who post about lifestyle, fashion, sustainable living, or city life.
3. For competitor_campaigns: think about what you've seen from Bata, Nike, Woodland, Allbirds store launches in India — what formats, what worked, what flopped.
4. Content hooks should be scroll-stopping — think viral-first."""


def research_city(
    city: str,
    area: str,
    opening_date: str,
    api_key: str,
    model: str = "claude-sonnet-4-20250514",
) -> dict:
    """
    Run deep city research using Claude API.

    Returns:
        dict with structured research report, or {"error": str} on failure.
    """
    client = Anthropic(api_key=api_key)

    user_prompt = f"""Research this city for a Neeman's shoe store launch campaign:

**City:** {city}
**Area/Locality:** {area or 'Not specified — cover the city broadly'}
**Store Opening Date:** {opening_date}

Produce a comprehensive research report. Be hyperlocal and specific. Reference real places, real cultural touchpoints, real consumer behaviors for {city}.

If an area is specified, go DEEP on that neighborhood — its reputation, who lives there, what the vibe is, walkability, nearby hotspots.

Consider what's happening around the opening date — festivals, weather, college schedules, cricket season, etc.

For influencer recommendations:
- Suggest REAL Instagram creators active in {city}
- 3-4 per tier: nano (1K-10K followers), micro (10K-100K), mid (100K-500K)
- Focus on lifestyle, fashion, sustainable living, city life creators
- Explain WHY each creator fits a Neeman's store launch

For competitor analysis:
- What shoe brands already operate in {city}?
- How do they launch stores on Instagram?
- What content gaps can Neeman's exploit?"""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=6000,
            system=RESEARCH_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = response.content[0].text.strip()

        # Try to extract JSON from response
        # Handle potential markdown fences
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        report = json.loads(raw)
        return report

    except json.JSONDecodeError:
        # If JSON parsing fails, return raw text as a report
        return {
            "city": city,
            "area": area,
            "raw_text": raw if "raw" in dir() else "Failed to parse response",
            "error": "Response was not valid JSON — raw text included above",
        }
    except Exception as e:
        return {"error": f"Research agent failed: {str(e)}"}


def stream_research_city(
    city: str,
    area: str,
    opening_date: str,
    api_key: str,
    model: str = "claude-sonnet-4-20250514",
):
    """
    Stream city research for live display, then parse at the end.
    Yields text chunks. Final result should be parsed by caller.
    """
    client = Anthropic(api_key=api_key)

    user_prompt = f"""Research this city for a Neeman's shoe store launch campaign:

**City:** {city}
**Area/Locality:** {area or 'Not specified — cover the city broadly'}
**Store Opening Date:** {opening_date}

Produce a comprehensive research report. Be hyperlocal and specific to {city}.
If an area is specified, go DEEP on that neighborhood.
Include real influencer recommendations and competitor analysis."""

    with client.messages.stream(
        model=model,
        max_tokens=6000,
        system=RESEARCH_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield text


def format_research_markdown(report: dict) -> str:
    """Convert structured research report to readable markdown."""
    if "error" in report and "raw_text" not in report:
        return f"**Error:** {report['error']}"

    if "raw_text" in report:
        return f"## Research Report: {report.get('city', 'Unknown')}\n\n{report['raw_text']}"

    lines = []
    city = report.get("city", "")

    ci = report.get("city_identity", {})
    lines.append(f"## {city} — {ci.get('tagline', '')}")
    lines.append("")
    lines.append(f"*{ci.get('city_personality', '')}*")
    lines.append("")

    lines.append("### Landmarks & Pride")
    for lm in ci.get("top_landmarks", []):
        lines.append(f"- {lm}")
    lines.append("")
    lines.append("**Cultural pride:**")
    for cp in ci.get("cultural_pride_points", []):
        lines.append(f"- {cp}")
    lines.append("")
    lines.append("**Local slang / references:**")
    for sl in ci.get("local_slang_references", []):
        lines.append(f"- {sl}")
    lines.append("")

    cp = report.get("consumer_profile", {})
    lines.append("### Consumer Profile")
    lines.append(f"- **Age:** {cp.get('dominant_age', '')}")
    lines.append(f"- **Lifestyle:** {cp.get('lifestyle', '')}")
    lines.append(f"- **Fashion:** {cp.get('fashion_sensibility', '')}")
    lines.append(f"- **Aspirations:** {cp.get('aspirations', '')}")
    lines.append(f"- **Pain points:** {cp.get('pain_points', '')}")
    lines.append(f"- **Digital behavior:** {cp.get('digital_behavior', '')}")
    lines.append("")

    rl = report.get("retail_landscape", {})
    lines.append("### Retail Landscape")
    lines.append("**Premium malls:** " + ", ".join(rl.get("premium_malls", [])))
    lines.append("**Shopping areas:** " + ", ".join(rl.get("key_shopping_areas", [])))
    lines.append("**Competitors present:** " + ", ".join(rl.get("competitor_presence", [])))
    lines.append("")

    # Competitor campaigns section
    cc = report.get("competitor_campaigns", {})
    if cc:
        lines.append("### Competitor Campaign Analysis")
        if cc.get("what_competitors_do"):
            lines.append(f"**What competitors do:** {cc['what_competitors_do']}")
        if cc.get("gaps_to_exploit"):
            lines.append(f"\n**Gaps to exploit:** {cc['gaps_to_exploit']}")
        if cc.get("trending_store_launch_formats"):
            lines.append(f"\n**Trending formats:** {cc['trending_store_launch_formats']}")
        lines.append("")

    # Content hooks section
    ch = report.get("content_hooks", {})
    if ch:
        lines.append("### Content Hooks & Viral Angles")
        if ch.get("viral_angles"):
            lines.append("**Viral angles:**")
            for va in ch["viral_angles"]:
                lines.append(f"- {va}")
        if ch.get("trending_formats"):
            lines.append("\n**Trending formats:**")
            for tf in ch["trending_formats"]:
                lines.append(f"- {tf}")
        if ch.get("local_memes_references"):
            lines.append("\n**Local memes/references:**")
            for lm in ch["local_memes_references"]:
                lines.append(f"- {lm}")
        lines.append("")

    co = report.get("campaign_opportunities", {})
    lines.append("### Campaign Opportunities")
    lines.append("**Local hooks:**")
    for hook in co.get("local_hooks", []):
        lines.append(f"- {hook}")
    lines.append(f"\n**Seasonal context:** {co.get('seasonal_context', '')}")
    lines.append(f"**Influencer tier:** {co.get('influencer_tier', '')}")
    lines.append("")

    # Influencer recommendations
    inf = report.get("influencer_recommendations", {})
    if inf:
        lines.append("### 🎯 Influencer Recommendations")
        for tier, tier_label in [("nano", "Nano (1K-10K)"), ("micro", "Micro (10K-100K)"), ("mid", "Mid-tier (100K-500K)")]:
            creators = inf.get(tier, [])
            if creators:
                lines.append(f"\n**{tier_label}:**")
                lines.append("")
                lines.append("| Handle | Followers | Niche | Why |")
                lines.append("|--------|-----------|-------|-----|")
                for c in creators:
                    handle = c.get("handle", "")
                    followers = c.get("followers", "")
                    niche = c.get("niche", "")
                    why = c.get("why", "")
                    lines.append(f"| {handle} | {followers} | {niche} | {why} |")
                lines.append("")

    lines.append("### Strategic Reasoning")
    lines.append(report.get("reasoning", ""))

    return "\n".join(lines)
