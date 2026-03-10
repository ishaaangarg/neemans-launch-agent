"""
Neeman's Store Launch Agent v2
================================
AI-powered campaign generator for hyperlocal retail store openings.
Type a city → get a complete Instagram launch campaign with AI-generated visuals.
"""

import streamlit as st
import json
import re
from datetime import datetime, timedelta

from utils.brand_loader import load_brand_context
from utils.helpers import export_campaign_markdown, export_campaign_docx
from agents.researcher import research_city, format_research_markdown
from agents.scraper import scrape_products
from agents.campaign_generator import stream_campaign
from agents.image_generator import (
    generate_batch,
    extract_image_prompts_from_campaign,
    VISUAL_MODELS,
)

# ──────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Neeman's Store Launch Agent",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# CUSTOM CSS
# ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600;700&display=swap');

.stApp { background-color: #F5F0E8; }

.main-header {
    font-family: 'Bebas Neue', sans-serif;
    color: #1B3A2D;
    font-size: 2.4rem;
    text-transform: uppercase;
    letter-spacing: 3px;
    margin-bottom: 0;
}
.sub-header {
    font-family: 'Inter', sans-serif;
    color: #6B6B6B;
    font-size: 1.0rem;
    margin-top: -8px;
    margin-bottom: 20px;
}

/* Cards */
.launch-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    margin: 10px 0;
    border-left: 5px solid #1B3A2D;
}
.launch-card.accent { border-left-color: #C4603B; }

.priority-card {
    background: linear-gradient(135deg, #1B3A2D 0%, #2D5A42 100%);
    border-radius: 12px;
    padding: 20px 24px;
    color: #F5F0E8;
    margin: 10px 0;
}
.priority-card h3 { color: #C4603B; margin-top: 0; }

/* Sidebar */
section[data-testid="stSidebar"] { background-color: #1B3A2D; }

/* Sidebar text — labels, markdown, captions */
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li,
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] .stCheckbox label span,
section[data-testid="stSidebar"] small,
section[data-testid="stSidebar"] .stCaption p,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: #F5F0E8 !important;
}
section[data-testid="stSidebar"] h3 {
    color: #C4603B;
    font-family: 'Inter', sans-serif;
}

/* Selectbox: selected value text inside white input must be DARK */
section[data-testid="stSidebar"] [data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-baseweb="select"] span[class*="option"],
section[data-testid="stSidebar"] [data-baseweb="select"] > div > div {
    color: #1B3A2D !important;
}

/* Selectbox dropdown options — dark text on white popup */
div[data-baseweb="popover"] li,
div[data-baseweb="popover"] [role="option"],
div[data-baseweb="popover"] [role="option"] span {
    color: #1B3A2D !important;
}

/* Text input placeholders should be visible but muted */
section[data-testid="stSidebar"] input::placeholder {
    color: #a0a0a0 !important;
}

/* Step boxes */
.step-box {
    background: #1B3A2D;
    color: #F5F0E8;
    border-radius: 10px;
    padding: 18px;
    text-align: center;
    font-family: 'Inter', sans-serif;
}
.step-box .step-num {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2rem;
    letter-spacing: 1px;
}
.step-box .step-label {
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    opacity: 0.7;
}

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
hr { border-color: #D4D4D0; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────
_defaults = {
    "city": "",
    "area": "",
    "opening_date": None,
    "store_address": "",
    "research_report": None,
    "research_markdown": None,
    "campaign_output": None,
    "generated_images": None,
    "selected_products": [],
    "products_list": None,
    "products_live": False,
    "generation_step": None,
    "visual_mode": "quick",
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<h2 style='font-family:Bebas Neue,sans-serif;color:#C4603B;"
        "letter-spacing:4px;margin-bottom:0'>N E E M A N ' S</h2>",
        unsafe_allow_html=True,
    )
    st.caption("Store Launch Agent v2")

    st.divider()
    st.markdown("### API Keys")
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="sk-ant-api03-...",
        help="[Get a key](https://console.anthropic.com/)",
    )

    st.divider()
    st.markdown("### Visual Generation")
    _visual_labels = {
        "No visuals": "off",
        "Quick — Flux Schnell (~$0.08)": "quick",
        "Shoe+ Scenes — Kontext Pro (~$1.05)": "shoe_plus",
    }
    visual_choice = st.selectbox(
        "Visual mode",
        options=list(_visual_labels.keys()),
        index=1,  # default to Quick
        help="Quick = generic AI visuals. Shoe+ = uses actual product shoe in each scene.",
    )
    visual_mode = _visual_labels[visual_choice]
    visuals_on = visual_mode != "off"

    together_key = ""
    if visuals_on:
        together_key = st.text_input(
            "Together AI Key",
            type="password",
            placeholder="tok-...",
            help="[Get a free key](https://api.together.ai/)",
        )

    st.divider()
    st.markdown("### Brand Context")
    brand_ctx, loaded_files = load_brand_context()
    for f in loaded_files:
        st.markdown(f"✅ {f}")
    st.caption(f"{len(brand_ctx):,} chars loaded")

    st.divider()
    st.markdown("### Products")
    # Load products
    if st.session_state["products_list"] is None:
        with st.spinner("Scraping Neeman's bestsellers..."):
            prods, is_live = scrape_products()
            st.session_state["products_list"] = prods
            st.session_state["products_live"] = is_live

    prods = st.session_state["products_list"]
    is_live = st.session_state["products_live"]

    if is_live:
        bestseller_count = sum(1 for p in prods if p.get("is_bestseller"))
        st.success(f"Live: {len(prods)} products ({bestseller_count} bestsellers)")
    else:
        st.warning(f"Fallback: {len(prods)} products (scraping failed)")

    # Product selection checkboxes
    st.caption("Select products to feature (⭐ = bestseller):")
    selected = []
    for i, p in enumerate(prods[:20]):
        badge = "⭐ " if p.get("is_bestseller") else ""
        label = f"{badge}{p['name']} — ₹{p['price']:,}"
        checked = st.checkbox(label, value=(i < 10), key=f"prod_{i}")
        if checked:
            selected.append(p)
    st.session_state["selected_products"] = selected
    st.caption(f"{len(selected)} products selected")

    st.divider()
    st.markdown("### Settings")
    model = st.selectbox(
        "Claude Model",
        ["claude-sonnet-4-20250514", "claude-haiku-4-20250514"],
        help="Sonnet = best quality. Haiku = fastest.",
    )

    st.divider()
    # Reset button
    if st.button("🔄 Start New Campaign", use_container_width=True):
        for k, v in _defaults.items():
            st.session_state[k] = v
        st.rerun()

    st.markdown("---")
    st.caption("Neeman's Store Launch Agent v2.0")
    st.caption("Built with Claude API + Streamlit")


# ──────────────────────────────────────────────
# MAIN CONTENT
# ──────────────────────────────────────────────
st.markdown(
    '<p class="main-header">Neeman\'s Store Launch Agent</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="sub-header">Type any Indian city &rarr; get a complete hyperlocal Instagram launch campaign with AI-generated visuals.</p>',
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────
# TABS
# ──────────────────────────────────────────────
tab_setup, tab_research, tab_campaign, tab_visuals = st.tabs([
    "📍 Launch Setup",
    "🔍 Research & Strategy",
    "📱 Campaign Assets",
    "🎨 AI Visuals",
])


# ═══════════════════════════════════════════════
# TAB 1: LAUNCH SETUP
# ═══════════════════════════════════════════════
with tab_setup:
    st.markdown("### Launch Details")

    col1, col2 = st.columns(2)
    with col1:
        city = st.text_input(
            "City",
            placeholder="Any Indian city or town — e.g. Siliguri, Kozhikode, Udaipur...",
            help="Type any city or town in India. No restrictions.",
        )

    with col2:
        area = st.text_input(
            "Area / Locality (optional)",
            placeholder="e.g. Koregaon Park, Indiranagar, Bandra...",
        )

    col3, col4 = st.columns(2)
    with col3:
        opening_date = st.date_input(
            "Store Opening Date",
            value=datetime.now().date() + timedelta(days=14),
        )
    with col4:
        store_address = st.text_input(
            "Store Address (optional)",
            placeholder="Shop 12, Phoenix Mall, Koregaon Park...",
        )

    st.markdown("---")

    # Generate button
    go = st.button(
        "▶ Generate Full Campaign",
        type="primary",
        use_container_width=True,
        disabled=not city or not api_key,
    )

    if not api_key:
        st.info("Enter your Anthropic API key in the sidebar to get started.")

    if not city and api_key:
        st.info("Type a city name to generate a campaign.")

    # ── GENERATION FLOW ──
    if go and city and api_key:
        st.session_state["city"] = city
        st.session_state["area"] = area
        st.session_state["opening_date"] = str(opening_date)
        st.session_state["store_address"] = store_address
        st.session_state["visual_mode"] = visual_mode

        # Clear previous results
        st.session_state["research_report"] = None
        st.session_state["research_markdown"] = None
        st.session_state["campaign_output"] = None
        st.session_state["generated_images"] = None

        # ── Step 1: Research ──
        with st.status(f"🔍 Researching {city} (culture, competitors, influencers)...", expanded=True) as status:
            st.write(f"Deep-diving into {city}'s culture, retail landscape, competitor campaigns, and influencer ecosystem...")
            try:
                report = research_city(
                    city, area, str(opening_date), api_key, model
                )
                if "error" in report and "raw_text" not in report:
                    st.error(f"Research failed: {report['error']}")
                    st.stop()

                st.session_state["research_report"] = report
                research_md = format_research_markdown(report)
                st.session_state["research_markdown"] = research_md
                status.update(label=f"✅ Research complete for {city}", state="complete")
            except Exception as e:
                st.error(f"Research agent error: {e}")
                st.stop()

        # ── Step 2: Campaign Generation ──
        st.markdown("---")
        st.subheader("📱 Generating Campaign...")

        response_box = st.empty()
        full = ""
        with st.spinner(f"Writing full campaign for {city}..."):
            try:
                for chunk in stream_campaign(
                    city=city,
                    area=area,
                    opening_date=str(opening_date),
                    research_report=st.session_state["research_report"],
                    selected_products=st.session_state["selected_products"],
                    brand_context=brand_ctx,
                    api_key=api_key,
                    model=model,
                    store_address=store_address,
                ):
                    full += chunk
                    # Show streaming with cursor
                    response_box.markdown(full + " **|**")
            except Exception as e:
                st.error(f"Campaign generation error: {e}")
                st.stop()

        response_box.empty()
        st.session_state["campaign_output"] = full
        st.success(f"✅ Full campaign generated for {city}!")

        # ── Step 3: Image Generation ──
        if visuals_on and together_key:
            mode_label = VISUAL_MODELS.get(visual_mode, {}).get("label", "Flux")

            # Get product shoe reference for Shoe+ mode
            ref_image_url = None
            if visual_mode == "shoe_plus" and st.session_state["selected_products"]:
                for prod in st.session_state["selected_products"]:
                    if prod.get("image_url"):
                        ref_image_url = prod["image_url"]
                        break

            with st.status(f"🎨 Generating AI visuals with {mode_label}...", expanded=True) as img_status:
                prompts = extract_image_prompts_from_campaign(full)
                if prompts:
                    st.write(f"Found {len(prompts)} image prompts. Generating with **{mode_label}**...")
                    progress = st.progress(0)

                    def _update(done, total):
                        progress.progress(done / total, text=f"Generating... {done}/{total}")

                    results = generate_batch(
                        prompts,
                        together_key,
                        mode=visual_mode,
                        ref_image_url=ref_image_url,
                        progress_callback=_update,
                    )
                    st.session_state["generated_images"] = results
                    success_count = sum(1 for r in results if r and r.get("image"))
                    img_status.update(
                        label=f"✅ Generated {success_count}/{len(prompts)} visuals ({mode_label})",
                        state="complete",
                    )
                else:
                    st.write("No image prompts found in campaign output.")
                    img_status.update(label="No visuals to generate", state="complete")

        st.balloons()
        st.info("Switch to the **Research & Strategy**, **Campaign Assets**, or **AI Visuals** tabs to explore your campaign.")

    # Landing state
    if not st.session_state["campaign_output"] and not go:
        st.markdown("---")
        st.markdown("#### How it works")
        c1, c2, c3, c4 = st.columns(4)
        steps = [
            ("1", "Enter city & date"),
            ("2", "AI researches city + competitors"),
            ("3", "Full campaign generated"),
            ("4", "AI visuals with real shoes"),
        ]
        for col, (num, label) in zip([c1, c2, c3, c4], steps):
            with col:
                st.markdown(
                    f'<div class="step-box"><div class="step-num">{num}</div>'
                    f'<div class="step-label">{label}</div></div>',
                    unsafe_allow_html=True,
                )

        st.markdown("")
        st.markdown("**What you get:**")
        st.markdown("""
- 🔥 Top 5 priority deployment-ready concepts
- 4 carousel concepts (24 slides with exact copy + AI visuals)
- 5 reel storyboards (teaser, city pride, mini-doc, product drop, BTS)
- 7-story Instagram arc (Day -3 to Day +1)
- 6 ready-to-use captions (short, medium, long)
- Full hashtag strategy (22+ hashtags)
- Real influencer recommendations with handles (nano, micro, mid)
- Competitor campaign analysis + differentiation hooks
- 20-item launch day content checklist
- AI-generated visuals featuring actual Neeman's shoes
""")


# ═══════════════════════════════════════════════
# TAB 2: RESEARCH & STRATEGY
# ═══════════════════════════════════════════════
with tab_research:
    if st.session_state["research_markdown"]:
        st.markdown(st.session_state["research_markdown"])

        # Show raw JSON
        if st.session_state["research_report"] and isinstance(st.session_state["research_report"], dict):
            with st.expander("View raw research data (JSON)"):
                st.json(st.session_state["research_report"])

        # Campaign strategy section (extract from campaign output)
        if st.session_state["campaign_output"]:
            st.markdown("---")
            campaign = st.session_state["campaign_output"]
            strategy_match = re.search(
                r"(# 1\. CAMPAIGN STRATEGY.*?)(?=# 2\.|$)",
                campaign,
                re.DOTALL,
            )
            if strategy_match:
                st.markdown("## Campaign Strategy")
                st.markdown(strategy_match.group(1))
    else:
        st.info("Generate a campaign from the **Launch Setup** tab to see research results here.")


# ═══════════════════════════════════════════════
# HELPER: Match images to campaign sections
# ═══════════════════════════════════════════════
def _get_images_for_section(section_text: str, all_images: list[dict] | None) -> list[dict]:
    """Find generated images whose prompts appear in this section."""
    if not all_images or not section_text:
        return []
    matches = []
    for img in all_images:
        if not img or not img.get("image"):
            continue
        # Check if this image's prompt text overlaps with the section
        prompt_words = set(img.get("prompt", "").lower().split()[:15])
        section_lower = section_text.lower()
        overlap = sum(1 for w in prompt_words if len(w) > 4 and w in section_lower)
        if overlap >= 3:
            matches.append(img)
    return matches[:3]  # max 3 images per section


# ═══════════════════════════════════════════════
# TAB 3: CAMPAIGN ASSETS
# ═══════════════════════════════════════════════
with tab_campaign:
    if st.session_state["campaign_output"]:
        campaign = st.session_state["campaign_output"]
        images = st.session_state.get("generated_images") or []

        # ── Priority Concepts (shown at top) ──
        priority_match = re.search(
            r"(# 2\. PRIORITY CONCEPTS.*?)(?=# 3\.|$)",
            campaign,
            re.DOTALL | re.IGNORECASE,
        )
        if priority_match:
            st.markdown(
                '<div class="priority-card"><h3>🔥 Priority Concepts — Deploy These First</h3></div>',
                unsafe_allow_html=True,
            )
            st.markdown(priority_match.group(1))
            st.markdown("---")

        # ── Section definitions with regex patterns ──
        sections = [
            ("📸 Carousel 1: Grand Arrival", r"# 3\. CAROUSEL.*?(?=# 4\.|$)", True),
            ("📸 Carousel 2: Lifestyle", r"# 4\. CAROUSEL.*?(?=# 5\.|$)", True),
            ("📸 Carousel 3: Sustainability", r"# 5\. CAROUSEL.*?(?=# 6\.|$)", True),
            ("📸 Carousel 4: Product Deep-Dive", r"# 6\. CAROUSEL.*?(?=# 7\.|$)", True),
            ("🎬 Reel 1: 15s Launch Teaser", r"# 7\. REEL.*?(?=# 8\.|$)", False),
            ("🎬 Reel 2: 30s City Pride", r"# 8\. REEL.*?(?=# 9\.|$)", False),
            ("🎬 Reel 3: 45s Mini-Documentary", r"# 9\. REEL.*?(?=# 10\.|$)", False),
            ("🎬 Reel 4: 20s Product Drop", r"# 10\. REEL.*?(?=# 11\.|$)", False),
            ("🎬 Reel 5: 30s BTS Tour", r"# 11\. REEL.*?(?=# 12\.|$)", False),
            ("📖 Stories Sequence", r"# 12\. INSTAGRAM.*?(?=# 13\.|$)", False),
            ("✍️ Caption Copy Bank", r"# 13\. CAPTION.*?(?=# 14\.|$)", False),
            ("#️⃣ Hashtag Strategy", r"# 14\. HASHTAG.*?(?=# 15\.|$)", False),
            ("🤝 Influencer Activation Plan", r"# 15\. INFLUENCER.*?(?=# 16\.|$)", False),
            ("✅ Launch Day Checklist", r"# 16\. LAUNCH.*", False),
        ]

        for title, pattern, show_images in sections:
            match = re.search(pattern, campaign, re.DOTALL | re.IGNORECASE)
            if match:
                section_text = match.group(0)
                section_images = _get_images_for_section(section_text, images) if show_images else []

                # Carousels expanded by default, others collapsed
                is_carousel = "Carousel" in title
                with st.expander(title, expanded=is_carousel):
                    if section_images:
                        # Side-by-side: images left, text right
                        img_col, text_col = st.columns([1, 1.5])
                        with img_col:
                            for si, simg in enumerate(section_images):
                                st.image(
                                    simg["image"],
                                    caption=f"AI Visual — {simg.get('label', f'Image {si+1}')}",
                                    use_container_width=True,
                                )
                        with text_col:
                            st.markdown(section_text)
                    else:
                        st.markdown(section_text)

                    # Download section
                    st.download_button(
                        "📋 Download this section",
                        data=section_text,
                        file_name=f"{title.split(':')[0].strip()}.md",
                        mime="text/markdown",
                        key=f"dl_{title}",
                    )

        # Full export
        st.markdown("---")
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        with col_exp1:
            md_export = export_campaign_markdown({
                "city": st.session_state.get("city", ""),
                "area": st.session_state.get("area", ""),
                "opening_date": st.session_state.get("opening_date", ""),
                "research_report": st.session_state.get("research_markdown", ""),
                "campaign_output": campaign,
            })
            st.download_button(
                "📥 Export Full Campaign (.md)",
                data=md_export,
                file_name=f"neemans_launch_{st.session_state.get('city', 'campaign').lower()}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col_exp2:
            try:
                docx_buf = export_campaign_docx({
                    "city": st.session_state.get("city", ""),
                    "area": st.session_state.get("area", ""),
                    "opening_date": st.session_state.get("opening_date", ""),
                    "research_report": st.session_state.get("research_markdown", ""),
                    "campaign_output": campaign,
                })
                st.download_button(
                    "📥 Export Full Campaign (.docx)",
                    data=docx_buf,
                    file_name=f"neemans_launch_{st.session_state.get('city', 'campaign').lower()}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
            except ImportError:
                st.button("DOCX export (install python-docx)", disabled=True, use_container_width=True)

        with col_exp3:
            with st.expander("View raw markdown"):
                st.code(campaign, language="markdown")
    else:
        st.info("Generate a campaign from the **Launch Setup** tab to see assets here.")


# ═══════════════════════════════════════════════
# TAB 4: AI VISUALS
# ═══════════════════════════════════════════════
with tab_visuals:
    if st.session_state["generated_images"]:
        images = st.session_state["generated_images"]
        success = [r for r in images if r and r.get("image")]
        failed = [r for r in images if r and not r.get("image")]

        mode_used = st.session_state.get("visual_mode", "quick")
        mode_label = VISUAL_MODELS.get(mode_used, {}).get("label", "Flux")
        st.markdown(f"### Generated Visuals ({len(success)}/{len(images)}) — {mode_label}")

        # Grid layout — 2 columns
        cols = st.columns(2)
        for i, result in enumerate(images):
            if not result:
                continue
            with cols[i % 2]:
                st.markdown(f"**{result['label']}** ({result['format']})")
                if result.get("image"):
                    st.image(result["image"], use_container_width=True)
                    st.download_button(
                        "📥 Download",
                        data=result["image"],
                        file_name=f"neemans_visual_{i+1}.png",
                        mime="image/png",
                        key=f"img_dl_{i}",
                    )
                else:
                    st.error(f"Failed: {result.get('error', 'Unknown error')}")

                with st.expander("View prompt"):
                    st.code(result["prompt"], language=None)

        # Show failed prompts for manual generation
        if failed:
            st.markdown("---")
            st.markdown("### Prompts for Manual Generation")
            st.caption("Use these in Midjourney, Leonardo AI, or Ideogram")
            for r in failed:
                st.code(r["prompt"], language=None)

    elif st.session_state["campaign_output"] and not together_key:
        st.warning("Enter your Together AI key in the sidebar to generate visuals.")

        # Still show the prompts
        prompts = extract_image_prompts_from_campaign(st.session_state["campaign_output"])
        if prompts:
            st.markdown("### Image Prompts (copy for Midjourney / Leonardo AI)")
            for i, p in enumerate(prompts):
                st.markdown(f"**{i+1}. {p.get('label', 'Visual')}** ({p['format']})")
                st.code(p["prompt"], language=None)

    elif st.session_state["campaign_output"]:
        # Campaign exists but no images yet
        if together_key:
            if st.button("🎨 Generate Visuals Now", type="primary"):
                prompts = extract_image_prompts_from_campaign(st.session_state["campaign_output"])
                if prompts:
                    # Get shoe reference
                    ref_image_url = None
                    if visual_mode == "shoe_plus" and st.session_state["selected_products"]:
                        for prod in st.session_state["selected_products"]:
                            if prod.get("image_url"):
                                ref_image_url = prod["image_url"]
                                break

                    progress = st.progress(0, text="Generating visuals...")

                    def _update(done, total):
                        progress.progress(done / total, text=f"Generating... {done}/{total}")

                    results = generate_batch(
                        prompts,
                        together_key,
                        mode=visual_mode,
                        ref_image_url=ref_image_url,
                        progress_callback=_update,
                    )
                    st.session_state["generated_images"] = results
                    st.session_state["visual_mode"] = visual_mode
                    progress.empty()
                    st.rerun()
                else:
                    st.warning("No image prompts found in campaign output.")
        else:
            st.info("Add Together AI key in sidebar to generate visuals.")
    else:
        st.info("Generate a campaign from the **Launch Setup** tab first.")
