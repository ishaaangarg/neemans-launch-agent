"""
Neeman's Store Launch Agent
============================
AI-powered campaign generator for hyperlocal retail store openings.
Paste a city → get a complete Instagram launch campaign with visuals.
"""

import streamlit as st
import json
import re
from datetime import datetime, timedelta

from utils.brand_loader import load_brand_context
from utils.helpers import export_campaign_markdown, export_campaign_docx
from brand.context import TOP_CITIES
from agents.researcher import research_city, format_research_markdown
from agents.scraper import scrape_products
from agents.campaign_generator import stream_campaign
from agents.image_generator import (
    generate_batch,
    extract_image_prompts_from_campaign,
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

/* Sidebar */
section[data-testid="stSidebar"] { background-color: #1B3A2D; }
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #F5F0E8 !important;
}
section[data-testid="stSidebar"] h3 {
    color: #C4603B;
    font-family: 'Inter', sans-serif;
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
    st.caption("Store Launch Agent")

    st.divider()
    st.markdown("### API Keys")
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="sk-ant-api03-...",
        help="[Get a key](https://console.anthropic.com/)",
    )
    together_key = st.text_input(
        "Together AI Key",
        type="password",
        placeholder="tok-...",
        help="[Get a key](https://api.together.ai/)",
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
        with st.spinner("Scraping Neeman's..."):
            prods, is_live = scrape_products()
            st.session_state["products_list"] = prods
            st.session_state["products_live"] = is_live

    prods = st.session_state["products_list"]
    is_live = st.session_state["products_live"]

    if is_live:
        st.success(f"Live: {len(prods)} products scraped")
    else:
        st.warning(f"Fallback: {len(prods)} products (scraping failed)")

    # Product selection checkboxes
    st.caption("Select products to feature:")
    selected = []
    for i, p in enumerate(prods[:15]):
        label = f"{p['name']} — ₹{p['price']:,}"
        checked = st.checkbox(label, value=(i < 8), key=f"prod_{i}")
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
    gen_images = st.toggle("Generate AI visuals", value=True, help="Uses Together AI (~$0.08)")

    st.divider()
    # Reset button
    if st.button("🔄 Start New Campaign", use_container_width=True):
        for k, v in _defaults.items():
            st.session_state[k] = v
        st.rerun()

    st.markdown("---")
    st.caption("Neeman's Store Launch Agent v1.0")
    st.caption("Built with Claude API + Streamlit")


# ──────────────────────────────────────────────
# MAIN CONTENT
# ──────────────────────────────────────────────
st.markdown(
    '<p class="main-header">Neeman\'s Store Launch Agent</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="sub-header">Enter a city &rarr; get a complete hyperlocal Instagram launch campaign with AI-generated visuals.</p>',
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
        city = st.selectbox(
            "City",
            options=[""] + TOP_CITIES,
            index=0,
            placeholder="Select or type a city...",
        )
        if not city:
            city = st.text_input("Or type a city:", placeholder="e.g. Pune")

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
        st.info("Select a city to generate a campaign.")

    # ── GENERATION FLOW ──
    if go and city and api_key:
        st.session_state["city"] = city
        st.session_state["area"] = area
        st.session_state["opening_date"] = str(opening_date)
        st.session_state["store_address"] = store_address

        # Clear previous results
        st.session_state["research_report"] = None
        st.session_state["research_markdown"] = None
        st.session_state["campaign_output"] = None
        st.session_state["generated_images"] = None

        # ── Step 1: Research ──
        with st.status(f"🔍 Researching {city}...", expanded=True) as status:
            st.write(f"Deep-diving into {city}'s culture, retail landscape, and consumer profile...")
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
        if gen_images and together_key:
            with st.status("🎨 Generating AI visuals...", expanded=True) as img_status:
                prompts = extract_image_prompts_from_campaign(full)
                if prompts:
                    st.write(f"Found {len(prompts)} image prompts. Generating...")
                    progress = st.progress(0)

                    def _update(done, total):
                        progress.progress(done / total, text=f"Generating... {done}/{total}")

                    results = generate_batch(prompts, together_key, progress_callback=_update)
                    st.session_state["generated_images"] = results
                    success_count = sum(1 for r in results if r and r.get("image"))
                    img_status.update(
                        label=f"✅ Generated {success_count}/{len(prompts)} visuals",
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
            ("2", "AI researches the city"),
            ("3", "Full campaign generated"),
            ("4", "AI visuals created"),
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
- 4 carousel concepts (24 slides with exact copy + visuals)
- 5 reel storyboards (teaser, launch day, mini-doc, product drop, BTS)
- 7-story Instagram arc (Day -3 to Day +1)
- 6 ready-to-use captions (short, medium, long)
- Full hashtag strategy (22+ hashtags)
- Influencer brief with sample DMs
- 20-item launch day content checklist
- AI-generated visuals for hero slides
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
            # Extract just the strategy section
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
# TAB 3: CAMPAIGN ASSETS
# ═══════════════════════════════════════════════
with tab_campaign:
    if st.session_state["campaign_output"]:
        campaign = st.session_state["campaign_output"]

        # Section definitions with regex patterns
        sections = [
            ("📸 Carousel Concept 1: Grand Arrival", r"# 2\. CAROUSEL.*?(?=# 3\.|$)"),
            ("📸 Carousel Concept 2: Lifestyle", r"# 3\. CAROUSEL.*?(?=# 4\.|$)"),
            ("📸 Carousel Concept 3: Sustainability", r"# 4\. CAROUSEL.*?(?=# 5\.|$)"),
            ("📸 Carousel Concept 4: Product Deep-Dive", r"# 5\. CAROUSEL.*?(?=# 6\.|$)"),
            ("🎬 Reel 1: 15s Launch Teaser", r"# 6\. REEL.*?(?=# 7\.|$)"),
            ("🎬 Reel 2: 30s City Pride", r"# 7\. REEL.*?(?=# 8\.|$)"),
            ("🎬 Reel 3: 45s Mini-Documentary", r"# 8\. REEL.*?(?=# 9\.|$)"),
            ("🎬 Reel 4: 20s Product Drop", r"# 9\. REEL.*?(?=# 10\.|$)"),
            ("🎬 Reel 5: 30s BTS Tour", r"# 10\. REEL.*?(?=# 11\.|$)"),
            ("📖 Stories Sequence", r"# 11\. INSTAGRAM.*?(?=# 12\.|$)"),
            ("✍️ Caption Copy Bank", r"# 12\. CAPTION.*?(?=# 13\.|$)"),
            ("#️⃣ Hashtag Strategy", r"# 13\. HASHTAG.*?(?=# 14\.|$)"),
            ("🤝 Influencer Brief", r"# 14\. INFLUENCER.*?(?=# 15\.|$)"),
            ("✅ Launch Day Checklist", r"# 15\. LAUNCH.*"),
        ]

        for title, pattern in sections:
            match = re.search(pattern, campaign, re.DOTALL | re.IGNORECASE)
            if match:
                with st.expander(title, expanded=False):
                    st.markdown(match.group(0))
                    # Copy button
                    st.download_button(
                        "📋 Download this section",
                        data=match.group(0),
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
            # View raw markdown
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

        st.markdown(f"### Generated Visuals ({len(success)}/{len(images)})")

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
                    progress = st.progress(0, text="Generating visuals...")

                    def _update(done, total):
                        progress.progress(done / total, text=f"Generating... {done}/{total}")

                    results = generate_batch(prompts, together_key, progress_callback=_update)
                    st.session_state["generated_images"] = results
                    progress.empty()
                    st.rerun()
                else:
                    st.warning("No image prompts found in campaign output.")
        else:
            st.info("Add Together AI key in sidebar to generate visuals.")
    else:
        st.info("Generate a campaign from the **Launch Setup** tab first.")
