# Neeman's Store Launch Agent

AI-powered campaign generator for hyperlocal retail store openings. Enter a city, get a complete Instagram launch campaign with AI-generated visuals.

## What It Does

1. **City Research Agent** — Deep-dives into the city's culture, consumer profile, retail landscape, and campaign opportunities using Claude API
2. **Product Scraper Agent** — Scrapes live product data from Neeman's Shopify store (with fallback catalog)
3. **Campaign Generator Agent** — Generates a complete 15-section launch campaign with streaming output
4. **Image Generator Agent** — Creates AI visuals using Together AI FLUX models

## Campaign Output

Each campaign includes:
- Campaign strategy with city-specific insight and tagline
- 4 carousel concepts (24 slides with exact copy + image prompts)
- 5 reel storyboards (teaser, city pride, mini-doc, product drop, BTS tour)
- 7-story Instagram arc (Day -3 to Day +1)
- 6 ready-to-use captions (short, medium, long)
- Full hashtag strategy (22+ hashtags)
- Influencer brief with sample DMs
- 20-item launch day content checklist
- AI-generated visuals for hero slides

## Setup

### Prerequisites
- Python 3.10+
- [Anthropic API key](https://console.anthropic.com/)
- [Together AI API key](https://api.together.ai/) (optional, for AI visuals)

### Install

```bash
git clone https://github.com/ishaaangarg/neemans-launch-agent.git
cd neemans-launch-agent
pip install -r requirements.txt
```

### Run

```bash
streamlit run app.py
```

Enter your API keys in the sidebar and select a city to generate a campaign.

## Project Structure

```
neemans-launch-agent/
  app.py                          # Main Streamlit app (4-tab UI)
  requirements.txt
  neemans_brand.md                # Brand knowledge base
  agents/
    researcher.py                 # Agent 1: City Research (Claude API)
    scraper.py                    # Agent 2: Product Scraper (Shopify JSON)
    campaign_generator.py         # Agent 3: Campaign Generator (Claude streaming)
    image_generator.py            # Agent 4: Image Generator (Together AI FLUX)
  brand/
    context.py                    # Hardcoded brand DNA + city list
  utils/
    brand_loader.py               # Loads brand context from filesystem
    helpers.py                    # Export helpers (markdown, docx)
  .streamlit/
    config.toml                   # Streamlit theme config
```

## Tech Stack

- **Frontend:** Streamlit
- **LLM:** Claude API (Anthropic) — Sonnet for quality, Haiku for speed
- **Image Generation:** Together AI FLUX.1-schnell
- **Product Data:** Shopify JSON API
- **Export:** Markdown + DOCX

## Configuration

### Brand Context
Drop any `.md` or `.txt` files in the project root to enrich the brand context. The app auto-loads:
- `neemans_brand.md` (included)
- `brand_context.md`, `brand_guidelines.md`, `claude.md` (if present)

### Models
- **Claude Sonnet** — Best campaign quality (default)
- **Claude Haiku** — Faster, cheaper generation
- **FLUX.1-schnell** — Free-tier image generation via Together AI

## License

MIT

---

*Built with Claude API + Streamlit*
