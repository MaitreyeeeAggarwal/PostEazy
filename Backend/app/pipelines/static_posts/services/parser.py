import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.gemini_client import (
    generate_carousel_slides,
    generate_hooks,
    generate_platform_copy,
)
from services.renderer import ResultDict, render_carousel, render_post


def aggregate_and_generate_hooks(
    file_analyses: List[Dict[str, Any]],
    job_id: Optional[str] = None,
    jobs: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Aggregate all file_analyses summaries and key_topics into one combined
    string/list, call generate_hooks() for 3 hooks, call generate_platform_copy()
    across 3 platforms (linkedin, instagram, twitter) producing 9 variants total,
    render static images for all 9 variants, and generate + render multi-slide
    carousels for LinkedIn and Instagram using Playwright and Jinja2 templates.
    """
    summaries: List[str] = []
    combined_topics: List[str] = []

    for item in file_analyses:
        # Extract only analysis payload, explicitly ignoring filename and file_path
        analysis = item.get("analysis", item) if isinstance(item, dict) else {}
        summary = analysis.get("summary")
        if summary and isinstance(summary, str):
            summaries.append(summary.strip())

        topics = analysis.get("key_topics", [])
        if isinstance(topics, list):
            for topic in topics:
                if topic:
                    topic_str = str(topic).strip()
                    if topic_str and topic_str not in combined_topics:
                        combined_topics.append(topic_str)

    aggregated_summary = "\n\n".join(summaries) if summaries else "Summary of analyzed content."

    # 1. Call generate_hooks with aggregated data
    hooks = generate_hooks(aggregated_summary=aggregated_summary, key_topics=combined_topics)

    # 2. Call generate_platform_copy across 3 platforms for each hook (3 x 3 = 9 variants)
    platforms = ["linkedin", "instagram", "twitter"]
    platform_copy_list: List[Dict[str, Any]] = []

    print(f"\n[PlatformCopy] Generating platform copy for {len(hooks)} hooks across {len(platforms)} platforms (9 variants)...", flush=True)
    for hook in hooks:
        hook_angle = hook.get("angle", "General Hook")
        for platform in platforms:
            copy_res = generate_platform_copy(hook=hook, platform=platform)
            # Log a line in terminal for each platform/hook combo as it completes
            print(f"[PlatformCopy] [{platform.upper()}] Generated copy for hook: '{hook_angle}'", flush=True)
            platform_copy_list.append({
                "hook_angle": hook_angle,
                "platform": platform,
                "copy": copy_res,
            })

    # 3. Static image rendering for each of the 9 copy variants
    renders_list: List[Dict[str, Any]] = []
    if job_id:
        renders_dir = Path("storage") / job_id / "renders"
        renders_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n[Renderer] Rendering static images for 9 variants into {renders_dir}...", flush=True)
        for hook_idx, hook in enumerate(hooks, start=1):
            hook_angle = hook.get("angle", f"Hook {hook_idx}")
            for platform in platforms:
                matching_item = next(
                    (item for item in platform_copy_list if item["hook_angle"] == hook_angle and item["platform"] == platform),
                    None
                )
                copy_dict = matching_item["copy"] if matching_item else {}
                output_filename = f"{platform}_{hook_idx}.png"
                output_file = renders_dir / output_filename

                try:
                    render_post(platform=platform, copy=copy_dict, output_path=str(output_file))
                    print(f"[render] saved storage/{job_id}/renders/{output_filename}", flush=True)
                    renders_list.append({
                        "platform": platform,
                        "hook_angle": hook_angle,
                        "image_path": str(output_file.resolve()),
                    })
                except Exception as e:
                    print(f"[Renderer] Error rendering {output_filename}: {e}", flush=True)

    # 4. Carousel slide generation and rendering for LinkedIn and Instagram (strictly exclude Twitter)
    carousels_list: List[Dict[str, Any]] = []
    carousel_platforms = ["linkedin", "instagram"]

    print(
        f"\n[Carousel] Starting carousel slide generation for {job_id or 'active job'} "
        f"(LinkedIn & Instagram across 3 hooks: 6 additional Gemini calls, this stage will take a bit longer)...",
        flush=True,
    )

    for hook_idx, hook in enumerate(hooks, start=1):
        hook_angle = hook.get("angle", f"Hook {hook_idx}")
        for cp in carousel_platforms:
            matching_copy_item = next(
                (item for item in platform_copy_list if item["hook_angle"] == hook_angle and item["platform"] == cp),
                None
            )
            copy_dict = matching_copy_item["copy"] if matching_copy_item else {}
            slides = generate_carousel_slides(copy=copy_dict, platform=cp)

            slide_entries: List[Dict[str, Any]] = []
            if job_id:
                try:
                    slide_paths = render_carousel(
                        platform=cp,
                        slides=slides,
                        job_id=job_id,
                        hook_index=hook_idx,
                    )
                    for slide_data, path_str in zip(slides, slide_paths):
                        slide_entries.append({
                            "slide_number": slide_data.get("slide_number", len(slide_entries) + 1),
                            "image_path": path_str,
                        })
                except Exception as e:
                    print(f"[Carousel] Error rendering {cp} carousel for hook {hook_idx}: {e}", flush=True)
            else:
                for s in slides:
                    slide_entries.append({
                        "slide_number": s.get("slide_number", len(slide_entries) + 1),
                        "image_path": "",
                    })

            carousels_list.append({
                "platform": cp,
                "hook_angle": hook_angle,
                "slides": slide_entries,
            })

    # 5. Store in jobs dictionary and clean up placement
    if jobs is not None and job_id is not None and job_id in jobs:
        target_job = jobs[job_id]
        result_dict = None
        if isinstance(target_job, dict):
            if "result" not in target_job or target_job["result"] is None:
                target_job["result"] = ResultDict()
            elif not isinstance(target_job["result"], ResultDict):
                target_job["result"] = ResultDict(target_job["result"])
            result_dict = target_job["result"]
        else:
            if target_job.result is None:
                target_job.result = ResultDict()
            elif not isinstance(target_job.result, ResultDict):
                target_job.result = ResultDict(target_job.result)
            result_dict = target_job.result

        if isinstance(result_dict, dict):
            # Clean up: ensure hooks, platform_copy, renders, and carousels do NOT appear at top level of result
            result_dict.pop("hooks", None)
            result_dict.pop("platform_copy", None)
            result_dict.pop("renders", None)
            result_dict.pop("carousels", None)

            # Update data level so fields only appear once, at the top level of data
            data_dict = result_dict.get("data")
            if isinstance(data_dict, dict):
                data_dict["hooks"] = hooks
                data_dict["platform_copy"] = platform_copy_list
                data_dict["renders"] = renders_list
                data_dict["carousels"] = carousels_list

                # Clean up metadata
                metadata_dict = data_dict.get("metadata")
                if isinstance(metadata_dict, dict):
                    metadata_dict.pop("hooks", None)
                    metadata_dict.pop("platform_copy", None)
                    metadata_dict.pop("renders", None)
                    metadata_dict.pop("carousels", None)
            else:
                result_dict["data"] = {
                    "hooks": hooks,
                    "platform_copy": platform_copy_list,
                    "renders": renders_list,
                    "carousels": carousels_list,
                }

    return hooks



class ParserService:
    """Service to parse and extract content from uploaded files."""

    def __init__(self, max_preview_chars: int = 2000):
        self.max_preview_chars = max_preview_chars

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parse an individual file and return metadata and text content."""
        path = Path(file_path)
        if not path.exists():
            return {
                "file_path": file_path,
                "error": "File does not exist",
                "content": "",
            }

        stat = path.stat()
        file_ext = path.suffix.lower()
        extracted_text = ""
        parse_status = "success"

        try:
            if file_ext in [".txt", ".md", ".json", ".csv", ".py", ".html", ".xml", ".yaml", ".yml"]:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    extracted_text = f.read(self.max_preview_chars)
            elif file_ext == ".pdf":
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(str(path))
                    t_list = [p.extract_text() or "" for p in reader.pages[:5]]
                    extracted_text = "\n".join(t_list).strip()[: self.max_preview_chars]
                    if not extracted_text:
                        extracted_text = f"[PDF Document: scanned or image-based] ({stat.st_size} bytes)"
                except Exception:
                    extracted_text = f"[PDF Document] ({stat.st_size} bytes)"
            else:
                extracted_text = f"[Binary or unsupported format: {file_ext}] ({stat.st_size} bytes)"
        except Exception as e:
            parse_status = "failed"
            extracted_text = f"Error reading file: {str(e)}"

        return {
            "filename": path.name,
            "file_path": str(path.resolve()),
            "extension": file_ext,
            "size_bytes": stat.st_size,
            "status": parse_status,
            "preview_text": extracted_text[: self.max_preview_chars],
        }

    def parse_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Parse multiple files from disk."""
        return [self.parse_file(fp) for fp in file_paths]

    def aggregate_and_generate_hooks(
        self,
        file_analyses: List[Dict[str, Any]],
        job_id: Optional[str] = None,
        jobs: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Aggregate file analyses and generate content hooks."""
        return aggregate_and_generate_hooks(
            file_analyses=file_analyses,
            job_id=job_id,
            jobs=jobs,
        )


# Default singleton instance
parser_service = ParserService()
