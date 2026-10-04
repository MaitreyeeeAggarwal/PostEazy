import html
from app.schemas import PresentationDeckScript, PresentationSlideLayout
from app.pipelines.presentation.core.theme_engine import get_theme_config
from app.pipelines.presentation.render.decorative import asset_data_uri, get_slide_decorations


def render_presentation_html(deck: PresentationDeckScript) -> str:
    """Renders a responsive, interactive 16:9 HTML presentation slide deck."""
    theme = get_theme_config(deck.theme)
    
    slides_html = []
    for s in deck.slides:
        decorations = get_slide_decorations(deck.theme, s.idx)
        frame_uri = asset_data_uri(decorations.frame)
        sticker_uris = [asset_data_uri(path) for path in (decorations.stickers or ((decorations.sticker,) if decorations.sticker else ()))]
        accent_uri = asset_data_uri(decorations.accent)
        slide_content = ""
        
        if s.layout == PresentationSlideLayout.TITLE_HERO:
            points_html = "".join([f"<li>{html.escape(pt)}</li>" for pt in s.body_points])
            slide_content = f"""
            <div class="slide-inner hero-slide flex flex-col justify-center items-center text-center">
                <div class="theme-badge mb-4">{html.escape(deck.target_audience.upper())} BRIEFING</div>
                <h1 class="slide-title text-5xl font-bold mb-4">{html.escape(s.heading)}</h1>
                <p class="slide-subtitle text-xl opacity-90 mb-8">{html.escape(s.subheading or deck.subtitle)}</p>
                {f'<ul class="hero-points flex gap-6 text-sm opacity-80">{points_html}</ul>' if points_html else ''}
            </div>
            """
            
        elif s.layout == PresentationSlideLayout.BIG_STAT:
            slide_content = f"""
            <div class="slide-inner flex items-center justify-between gap-12">
                <div class="w-1/2">
                    <div class="theme-badge mb-3">KEY METRIC</div>
                    <h2 class="slide-heading text-3xl font-bold mb-4">{html.escape(s.heading)}</h2>
                    <p class="text-lg text-secondary mb-6">{html.escape(s.subheading or "")}</p>
                    <ul class="body-list">
                        {"".join([f"<li>{html.escape(pt)}</li>" for pt in s.body_points])}
                    </ul>
                </div>
                <div class="w-1/2 stat-card text-center p-10 rounded-2xl">
                    <div class="stat-number text-7xl font-bold accent-text mb-2">{html.escape(s.stat_number or "100%")}</div>
                    <div class="stat-label text-lg font-semibold">{html.escape(s.stat_label or "Impact Rating")}</div>
                </div>
            </div>
            """
            
        elif s.layout == PresentationSlideLayout.FEATURE_CARDS:
            cards_html = []
            for item in s.card_items:
                t = html.escape(item.get("title", "Insight"))
                d = html.escape(item.get("desc", ""))
                cards_html.append(f"""
                <div class="feature-card p-6 rounded-xl border">
                    <div class="card-icon text-2xl mb-3">💡</div>
                    <h3 class="text-xl font-bold mb-2">{t}</h3>
                    <p class="text-sm opacity-85 leading-relaxed">{d}</p>
                </div>
                """)
            slide_content = f"""
            <div class="slide-inner">
                <div class="theme-badge mb-2">STRATEGIC PILLARS</div>
                <h2 class="slide-heading text-3xl font-bold mb-6">{html.escape(s.heading)}</h2>
                <div class="grid grid-cols-3 gap-6">
                    {"".join(cards_html)}
                </div>
            </div>
            """
            
        elif s.layout == PresentationSlideLayout.PROCESS_STEPPER:
            steps_html = []
            for idx, item in enumerate(s.card_items, start=1):
                t = html.escape(item.get("title", f"Step {idx}"))
                d = html.escape(item.get("desc", ""))
                steps_html.append(f"""
                <div class="step-card flex-1 p-5 rounded-xl border relative">
                    <div class="step-num w-8 h-8 rounded-full accent-bg font-bold flex items-center justify-center mb-3">{idx}</div>
                    <h4 class="font-bold text-lg mb-1">{t}</h4>
                    <p class="text-xs opacity-80">{d}</p>
                </div>
                """)
            slide_content = f"""
            <div class="slide-inner">
                <div class="theme-badge mb-2">EXECUTION WORKFLOW</div>
                <h2 class="slide-heading text-3xl font-bold mb-8">{html.escape(s.heading)}</h2>
                <div class="flex gap-4 items-stretch">
                    {"".join(steps_html)}
                </div>
            </div>
            """
            
        else:  # SPLIT_IMAGE_TEXT / END_CTA / Fallback
            pts = "".join([f"<li class='mb-3 flex items-start gap-2'><span>✦</span> {html.escape(pt)}</li>" for pt in s.body_points])
            slide_content = f"""
            <div class="slide-inner flex flex-col justify-center">
                <div class="theme-badge mb-2">SUMMARY & TAKEAWAYS</div>
                <h2 class="slide-heading text-4xl font-bold mb-6">{html.escape(s.heading)}</h2>
                {f'<p class="text-xl mb-6 opacity-90">{html.escape(s.subheading)}</p>' if s.subheading else ''}
                <ul class="text-lg space-y-3">
                    {pts}
                </ul>
            </div>
            """
            
        slides_html.append(f"""
        <section class="slide-card" id="slide-{s.idx}">
            {f'<img class="decor-frame" src="{frame_uri}" alt="" aria-hidden="true">' if frame_uri else ''}
            {''.join(f'<img class="decor-sticker decor-sticker-{index}" src="{uri}" alt="" aria-hidden="true">' for index, uri in enumerate(sticker_uris) if uri)}
            {f'<img class="decor-accent" src="{accent_uri}" alt="" aria-hidden="true">' if accent_uri else ''}
            {slide_content}
            <div class="slide-footer">
                <span>{html.escape(deck.title)}</span>
                <span>Slide {s.idx} of {len(deck.slides)}</span>
            </div>
        </section>
        """)

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(deck.title)}</title>
<link href="https://fonts.googleapis.com/css2?family=Quicksand:wght@500;700&family=Nunito+Sans:wght@400;600;700&family=Fraunces:ital,wght@0,600;1,400&display=swap" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>
<style>
    :root {{
        --bg: {theme["bg"]};
        --surface: {theme["surface"]};
        --border: {theme["surface_border"]};
        --text-primary: {theme["text_primary"]};
        --text-secondary: {theme["text_secondary"]};
        --accent: {theme["accent"]};
        --accent-sec: {theme["accent_secondary"]};
        --font-heading: {theme["font_family_heading"]};
        --font-body: {theme["font_family_body"]};
        --card-bg: {theme["card_bg"]};
        --card-shadow: {theme["card_shadow"]};
        --badge-bg: {theme["badge_bg"]};
        --badge-text: {theme["badge_text"]};
    }}
    body {{
        background-color: var(--bg);
        color: var(--text-primary);
        font-family: var(--font-body);
        margin: 0;
        padding: 0;
        overflow-x: hidden;
    }}
    h1, h2, h3, h4, .slide-title, .slide-heading {{
        font-family: var(--font-heading);
    }}
    .presentation-container {{
        width: 100vw;
        height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        items: center;
        position: relative;
    }}
    .slide-card {{
        width: 88vw;
        max-width: 1280px;
        height: 78vh;
        max-height: 720px;
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 1.5rem;
        box-shadow: var(--card-shadow);
        padding: 3.5rem;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        display: none;
        box-sizing: border-box;
        overflow: hidden;
    }}
    .slide-card.active {{
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        animation: fadeIn 0.3s ease-out;
    }}
    .slide-inner {{ position: relative; z-index: 2; }}
    .decor-frame {{ position:absolute; inset:0; width:100%; height:100%; object-fit:fill; opacity:.52; pointer-events:none; z-index:1; }}
    .decor-sticker {{ position:absolute; width:11%; max-width:124px; object-fit:contain; opacity:.9; pointer-events:none; z-index:1; }}
    .decor-sticker-0 {{ right:4%; top:7%; transform:rotate(8deg); }}
    .decor-sticker-1 {{ left:4%; top:16%; transform:rotate(-11deg); width:9%; opacity:.86; }}
    .decor-sticker-2 {{ right:5%; top:31%; transform:rotate(13deg); width:8%; opacity:.82; }}
    .decor-accent {{ position:absolute; width:18%; max-width:190px; left:4%; bottom:7%; object-fit:contain; opacity:.66; pointer-events:none; z-index:1; transform:rotate(-7deg); }}
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translate(-50%, -48%); }}
        to {{ opacity: 1; transform: translate(-50%, -50%); }}
    }}
    .theme-badge {{
        display: inline-block;
        background: var(--badge-bg);
        color: var(--badge-text);
        font-weight: 700;
        font-size: 0.75rem;
        letter-spacing: 0.1em;
        padding: 0.35rem 0.85rem;
        border-radius: 9999px;
    }}
    .accent-text {{ color: var(--accent); }}
    .accent-bg {{ background-color: var(--accent); color: #ffffff; }}
    .feature-card, .step-card, .stat-card {{
        background: var(--surface);
        border-color: var(--border);
    }}
    .slide-footer {{
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
        opacity: 0.6;
        border-top: 1px solid var(--border);
        padding-top: 1rem;
        margin-top: 1.5rem;
    }}
    .controls-bar {{
        position: fixed;
        bottom: 1.5rem;
        left: 50%;
        transform: translateX(-50%);
        display: flex;
        gap: 1rem;
        z-index: 50;
        background: var(--surface);
        border: 1px solid var(--border);
        padding: 0.5rem 1.25rem;
        border-radius: 9999px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
    }}
    .control-btn {{
        background: transparent;
        border: none;
        color: var(--text-primary);
        font-weight: 700;
        cursor: pointer;
        padding: 0.25rem 0.75rem;
    }}
</style>
</head>
<body>
<div class="presentation-container">
    {"".join(slides_html)}
</div>

<div class="controls-bar">
    <button class="control-btn" onclick="prevSlide()">← Prev</button>
    <span id="slideCounter" style="font-size:0.9rem; align-self:center;">1 / {len(deck.slides)}</span>
    <button class="control-btn" onclick="nextSlide()">Next →</button>
</div>

<script>
    let currentIdx = 0;
    const slides = document.querySelectorAll('.slide-card');
    const counter = document.getElementById('slideCounter');

    function showSlide(idx) {{
        slides.forEach((s, i) => s.classList.toggle('active', i === idx));
        counter.textContent = (idx + 1) + ' / ' + slides.length;
    }}

    function nextSlide() {{
        if (currentIdx < slides.length - 1) {{
            currentIdx++;
            showSlide(currentIdx);
        }}
    }}

    function prevSlide() {{
        if (currentIdx > 0) {{
            currentIdx--;
            showSlide(currentIdx);
        }}
    }}

    document.addEventListener('keydown', (e) => {{
        if (e.key === 'ArrowRight' || e.key === ' ') nextSlide();
        if (e.key === 'ArrowLeft') prevSlide();
    }});

    showSlide(0);
</script>
</body>
</html>
"""
    return full_html
