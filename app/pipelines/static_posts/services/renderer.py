import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

CANVAS_SIZES: Dict[str, Tuple[int, int]] = {
    "linkedin": (1200, 627),
    "instagram": (1080, 1080),
    "twitter": (1600, 900),
    "linkedin_carousel": (1080, 1350),
    "instagram_carousel": (1080, 1080),
}


class ResultDict(dict):
    """Dictionary that transparently provides access to nested data keys."""

    def __getitem__(self, key: str) -> Any:
        if key in self:
            return super().__getitem__(key)
        data = super().get("data")
        if isinstance(data, dict) and key in data:
            return data[key]
        return super().__getitem__(key)

    def get(self, key: str, default: Any = None) -> Any:
        if key in self:
            return super().get(key, default)
        data = super().get("data")
        if isinstance(data, dict) and key in data:
            return data.get(key, default)
        return default



def _sync_render(width: int, height: int, rendered_html: str, out_str: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})
        page.set_content(rendered_html, wait_until="load")
        page.screenshot(path=out_str, full_page=False)
        browser.close()


def render_post(platform: str, copy: dict, output_path: str) -> str:
    """
    Render static image for a social media post using Jinja2 templates and Playwright.
    Canvas sizes:
      - linkedin: 1200x627
      - instagram: 1080x1080
      - twitter: 1600x900
    Saves screenshot PNG to output_path and returns output_path.
    """
    from jinja2 import Environment, FileSystemLoader

    platform_normalized = (platform or "twitter").strip().lower()
    if platform_normalized not in CANVAS_SIZES:
        platform_normalized = "twitter"

    width, height = CANVAS_SIZES[platform_normalized]

    # Find templates directory
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=True,
    )

    template_name = f"{platform_normalized}.html"
    template = env.get_template(template_name)

    headline = copy.get("headline", "") if isinstance(copy, dict) else ""
    subtext = copy.get("subtext", "") if isinstance(copy, dict) else ""
    caption = copy.get("caption", "") if isinstance(copy, dict) else ""

    rendered_html = template.render(
        headline=headline,
        subtext=subtext,
        caption=caption,
    )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out_str = str(out.resolve())

    # Handle running inside an existing asyncio event loop (e.g. FastAPI background tasks)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(_sync_render, width, height, rendered_html, out_str).result()
    else:
        _sync_render(width, height, rendered_html, out_str)

    return out_str


def render_carousel(platform: str, slides: list[dict], job_id: str, hook_index: int) -> list[str]:
    """
    Render carousel slide images for a social media post using Jinja2 templates and Playwright.
    Only supports 'linkedin' (1080x1350) and 'instagram' (1080x1080).
    Saves each slide screenshot PNG to:
      storage/{job_id}/renders/{platform}_carousel_{hook_index}_slide{slide_number}.png
    Logs:
      [render] saved storage/{job_id}/renders/{platform}_carousel_{hook_index}_slide{slide_number}.png
    Returns list of generated file paths.
    """
    from jinja2 import Environment, FileSystemLoader

    platform_normalized = (platform or "linkedin").strip().lower()
    if platform_normalized not in ["linkedin", "instagram"]:
        platform_normalized = "linkedin"

    canvas_key = f"{platform_normalized}_carousel"
    width, height = CANVAS_SIZES.get(canvas_key, (1080, 1080))

    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=True,
    )

    template_name = f"{platform_normalized}_carousel_slide.html"
    template = env.get_template(template_name)

    renders_dir = Path("storage") / job_id / "renders"
    renders_dir.mkdir(parents=True, exist_ok=True)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    total_slides = len(slides)
    generated_paths: List[str] = []

    for idx, slide in enumerate(slides, start=1):
        slide_number = slide.get("slide_number", idx)
        slide_type = slide.get("slide_type", "content")
        title = slide.get("title", "")
        body = slide.get("body", "")

        rendered_html = template.render(
            slide_number=slide_number,
            total_slides=total_slides,
            slide_type=slide_type,
            title=title,
            body=body,
            platform=platform_normalized,
        )

        output_filename = f"{platform_normalized}_carousel_{hook_index}_slide{slide_number}.png"
        output_file = renders_dir / output_filename
        out_str = str(output_file.resolve())

        if loop and loop.is_running():
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(_sync_render, width, height, rendered_html, out_str).result()
        else:
            _sync_render(width, height, rendered_html, out_str)

        print(f"[render] saved storage/{job_id}/renders/{output_filename}", flush=True)
        generated_paths.append(out_str)

    return generated_paths


class RendererService:
    """Service to format and render generated outputs for client consumption."""

    def render_json_result(self, job_id: str, generated_data: Dict[str, Any]) -> ResultDict:
        """Render final output structure for API response."""
        return ResultDict({
            "job_id": job_id,
            "rendered_at": datetime.now(timezone.utc).isoformat(),
            "status": "ready",
            "data": generated_data,
            "render_format": "json",
        })

    def render_post(self, platform: str, copy: dict, output_path: str) -> str:
        """Render post static image using Jinja2 and Playwright."""
        return render_post(platform=platform, copy=copy, output_path=output_path)

    def render_carousel(self, platform: str, slides: list[dict], job_id: str, hook_index: int) -> list[str]:
        """Render carousel slides to images using Jinja2 and Playwright."""
        return render_carousel(platform=platform, slides=slides, job_id=job_id, hook_index=hook_index)

    def render_markdown(self, job_id: str, generated_data: Dict[str, Any]) -> str:
        """Render markdown formatted report with structured file analyses."""
        summary = generated_data.get("summary", "No summary available.")
        file_analyses: List[Dict[str, Any]] = generated_data.get("file_analyses", [])
        file_count = generated_data.get("processed_file_count", len(file_analyses))

        sections = [
            f"# Analysis Report for Job `{job_id}`\n",
            f"**Rendered At:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            f"**Files Analyzed:** {file_count}\n",
            f"## Overall Summary\n{summary}\n",
        ]

        if file_analyses:
            sections.append("## File Analysis Details\n")
            for idx, item in enumerate(file_analyses, start=1):
                fname = item.get("filename", f"File #{idx}")
                analysis = item.get("analysis", {})
                modality = analysis.get("modality", "N/A")
                file_summary = analysis.get("summary", "N/A")
                topics = ", ".join(analysis.get("key_topics", [])) or "None identified"
                entities = ", ".join(analysis.get("entities", [])) or "None identified"
                tone = analysis.get("suggested_tone", "N/A")
                visuals = ", ".join(analysis.get("notable_visual_elements", [])) or "None"

                sections.append(
                    f"### {idx}. {fname}\n"
                    f"- **Modality:** {modality}\n"
                    f"- **Summary:** {file_summary}\n"
                    f"- **Key Topics:** {topics}\n"
                    f"- **Entities:** {entities}\n"
                    f"- **Suggested Tone:** {tone}\n"
                    f"- **Notable Visual Elements:** {visuals}\n"
                )

        hooks: List[Dict[str, Any]] = generated_data.get("hooks", [])
        if hooks:
            sections.append("## Generated Social Media Content Hooks\n")
            for idx, hook in enumerate(hooks, start=1):
                angle = hook.get("angle", "Hook")
                headline = hook.get("headline", "")
                why = hook.get("why_it_works", "")
                sections.append(
                    f"**Hook {idx} ({angle})**\n"
                    f"> \"{headline}\"\n\n"
                    f"*Why it works:* {why}\n"
                )

        platform_copy: List[Dict[str, Any]] = generated_data.get("platform_copy", [])
        if platform_copy:
            sections.append("## Platform-Specific Copywriting (9 Variants)\n")
            for item in platform_copy:
                hook_angle = item.get("hook_angle", "Hook")
                platform_name = item.get("platform", "platform").capitalize()
                copy = item.get("copy", {})
                hashtags_str = " ".join(copy.get("hashtags", []))
                sections.append(
                    f"### [{platform_name}] {hook_angle}\n"
                    f"**Headline:** {copy.get('headline', '')}\n\n"
                    f"**Subtext:** {copy.get('subtext', '')}\n\n"
                    f"**Caption:**\n{copy.get('caption', '')}\n\n"
                    f"**Hashtags:** {hashtags_str}\n\n"
                    f"**CTA:** {copy.get('cta', '')}\n"
                )

        return "\n".join(sections)


# Default singleton instance
renderer_service = RendererService()
