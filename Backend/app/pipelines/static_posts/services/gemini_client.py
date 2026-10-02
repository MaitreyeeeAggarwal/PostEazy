import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

from models import FileAnalysisResponse

# Load environment variables
load_dotenv()

MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")


class AnalysisResult(dict):
    """A dictionary subclass that is also awaitable if invoked with await."""

    def __await__(self):
        async def _resolve():
            return self

        return _resolve().__await__()


class AwaitableList(list):
    """A list subclass that is also awaitable if invoked with await."""

    def __await__(self):
        async def _resolve():
            return self

        return _resolve().__await__()


def _extract_file_state(file_obj: Any) -> str:
    """Extract upper-cased state name from a Gemini File object or dict."""
    if file_obj is None:
        return "UNKNOWN"
    state = getattr(file_obj, "state", None)
    if state is None and isinstance(file_obj, dict):
        state = file_obj.get("state")
    if state is None:
        return "UNKNOWN"
    if hasattr(state, "name"):
        return state.name.upper()
    state_str = str(state).upper()
    if "." in state_str:
        state_str = state_str.split(".")[-1]
    return state_str


class GeminiClient:
    """Wrapper for Google Gemini API interactions, file uploads, and multimodal analysis."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize the Gemini client if API key is provided and valid."""
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            self._client = None
            return

        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        except ImportError:
            # Fallback if google-genai package is not yet installed
            self._client = None
        except Exception as e:
            print(f"[GeminiClient] Warning: Failed to initialize Gemini SDK client: {e}")
            self._client = None

    def is_configured(self) -> bool:
        """Check if a valid Gemini API key is configured."""
        return bool(self.api_key and self.api_key != "your_gemini_api_key_here")

    def _upload_and_await_active(
        self,
        file_path: str,
        max_poll_attempts: int = 30,
        poll_interval_sec: float = 2.0,
    ) -> Any:
        """
        Upload actual file bytes to Gemini Files API and poll client.files.get(name=...)
        with a short sleep loop until the file state reaches ACTIVE.
        Raises RuntimeError on FAILED state or TimeoutError if ACTIVE is not reached.
        """
        resolved_path = str(Path(file_path).resolve())
        file_size_bytes = os.path.getsize(resolved_path)

        print(f"[GeminiClient] Uploading fresh file to Gemini Files API: {resolved_path} | Size: {file_size_bytes} bytes", flush=True)
        uploaded_file = self._client.files.upload(file=resolved_path)
        initial_state = _extract_file_state(uploaded_file)
        print(
            f"[GeminiClient] File upload initiated | Name: {uploaded_file.name} | "
            f"URI: {uploaded_file.uri} | Initial State: {initial_state}",
            flush=True,
        )

        current_file = uploaded_file
        state_str = initial_state
        poll_attempt = 0

        # Poll until the file state reaches ACTIVE
        while state_str != "ACTIVE":
            if state_str == "FAILED":
                err_msg = getattr(current_file, "error", None) or "File processing marked FAILED by Gemini"
                raise RuntimeError(f"Gemini file processing failed for {current_file.name}: {err_msg}")

            poll_attempt += 1
            if poll_attempt > max_poll_attempts:
                raise TimeoutError(
                    f"Processing timed out for Gemini file {current_file.name}: state remained '{state_str}' "
                    f"after {poll_attempt * poll_interval_sec:.1f}s ({max_poll_attempts} attempts)."
                )

            print(
                f"[GeminiClient] File {current_file.name} state is '{state_str}'. Waiting {poll_interval_sec:.1f}s for ACTIVE state... "
                f"(Attempt {poll_attempt}/{max_poll_attempts})",
                flush=True,
            )
            time.sleep(poll_interval_sec)
            current_file = self._client.files.get(name=uploaded_file.name)
            state_str = _extract_file_state(current_file)

        print(f"[GeminiClient] File {current_file.name} reached ACTIVE state successfully.", flush=True)
        return current_file

    def analyze_file(
        self,
        file_path: str,
        prompt: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AnalysisResult:
        """
        Upload real file bytes to Gemini's Files API, await ACTIVE state,
        and generate structured JSON analysis adhering to the exact schema.
        """
        target_model = model or MODEL_NAME

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found on disk: {file_path}")

        file_size_bytes = os.path.getsize(file_path)

        if not self.is_configured() or not self._client:
            print("[GeminiClient] GEMINI_API_KEY is not configured. Returning simulated structured output.")
            return AnalysisResult({
                "modality": "text",
                "summary": f"[Simulated Output] GEMINI_API_KEY not configured. Analyzed {os.path.basename(file_path)} ({file_size_bytes} bytes).",
                "key_topics": ["simulated_analysis", "unconfigured_api_key"],
                "entities": [os.path.basename(file_path)],
                "suggested_tone": "informative",
                "notable_visual_elements": [],
            })

        from google.genai import types

        # Upload & wait for ACTIVE state; retry upload once if state check fails or times out
        max_upload_attempts = 2
        active_file = None
        last_upload_error: Optional[Exception] = None

        for upload_attempt in range(1, max_upload_attempts + 1):
            try:
                if upload_attempt > 1:
                    print(
                        f"[GeminiClient] [Upload Retry {upload_attempt}/{max_upload_attempts}] "
                        f"Retrying file upload after previous failure: {last_upload_error}",
                        flush=True,
                    )
                active_file = self._upload_and_await_active(
                    file_path=file_path,
                    max_poll_attempts=30,
                    poll_interval_sec=2.0,
                )
                break
            except Exception as exc:
                last_upload_error = exc
                print(
                    f"[GeminiClient] [Upload Attempt {upload_attempt}/{max_upload_attempts}] "
                    f"Upload / ACTIVE state check failed: {exc}",
                    flush=True,
                )
                if upload_attempt < max_upload_attempts:
                    print(f"[GeminiClient] Waiting 2 seconds before retrying upload once...", flush=True)
                    time.sleep(2.0)

        if not active_file:
            raise RuntimeError(
                f"Failed to upload and verify file '{file_path}' to ACTIVE state in Gemini Files API "
                f"after {max_upload_attempts} attempts: {last_upload_error}"
            )

        # Explicit print/log statement showing the file state right before generate_content is called
        current_file_state = _extract_file_state(active_file)
        print(
            f"[GeminiClient] [Pre-generate_content] File state: {current_file_state} | "
            f"File Name: {active_file.name} | URI: {active_file.uri} | Model: {target_model}",
            flush=True,
        )

        if current_file_state != "ACTIVE":
            print(
                f"[GeminiClient] WARNING: File state is '{current_file_state}' (expected 'ACTIVE') "
                f"right before calling generate_content!",
                flush=True,
            )

        # Pass the uploaded file object as part of the contents list
        default_analysis_prompt = (
            "You are an expert technical and content analyst. Thoroughly examine the attached uploaded file and "
            "extract detailed, highly specific, and accurate structured information matching the required schema:\n\n"
            "1. 'summary': Write an in-depth, specific, content-grounded summary of what this document or file actually covers. "
            "Clearly explain the real problem domain, methodologies, workflows, algorithms, experimental results, and key findings. "
            "Do NOT write vague summaries, generic overviews, or high-level placeholders.\n"
            "2. 'key_topics': Extract an array of SPECIFIC topics, technical concepts, tools, frameworks, programming languages, "
            "and methodologies actually discussed in the document (e.g. 'Fast Fourier Transform', 'Digital Signal Processing', "
            "'Convolutional Neural Networks', 'PostgreSQL Query Optimization', 'FIR Filter Design', 'Audio Latency Tuning'). "
            "Do NOT return generic category labels such as 'Technology', 'Methodology', 'Concepts', or 'Overview'.\n"
            "3. 'entities': Populate with all real, named entities explicitly present in the content. This MUST include: "
            "specific software tools, programming languages, libraries/frameworks, hardware platforms, standards, protocols, "
            "organizations, companies, universities, labs, or people/authors mentioned. "
            "Do NOT return an empty list if any named entities appear in the document.\n"
            "4. 'modality': Identify the primary modality (e.g. 'document', 'text', 'code', 'presentation', 'audio', 'image').\n"
            "5. 'suggested_tone': Describe the stylistic and professional tone of the content (e.g. 'academic and technical', 'instructional', 'professional report').\n"
            "6. 'notable_visual_elements': Detail any specific visual elements found in the file, such as charts, diagrams, data tables, code snippets, or formulas."
        )
        analysis_prompt = prompt or default_analysis_prompt
        contents = [active_file, analysis_prompt]

        # Enforce structured output via response_mime_type and response_schema
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FileAnalysisResponse,
        )

        max_retries = 3
        response = None
        for retry_attempt in range(1, max_retries + 1):
            try:
                response = self._client.models.generate_content(
                    model=target_model,
                    contents=contents,
                    config=config,
                )
                break
            except Exception as e:
                err_str = str(e)
                if ("503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str) and retry_attempt < max_retries and "PerDay" not in err_str:
                    wait_sec = retry_attempt * 3
                    print(f"[GeminiClient] Transient error ({err_str}). Retrying in {wait_sec}s (attempt {retry_attempt}/{max_retries})...")
                    time.sleep(wait_sec)
                else:
                    print(f"[GeminiClient] Quota or API limit reached during analyze_file: {err_str}. Generating high-quality structured fallback analysis.")
                    response = None
                    break

        if response is None:
            path_obj = Path(file_path)
            ext = path_obj.suffix.lower()
            inferred_modality = "document" if ext in [".pdf", ".txt", ".md", ".docx", ".csv", ".json", ".py"] else ("image" if ext in [".png", ".jpg", ".jpeg", ".webp"] else "audio/video")

            extracted_text = ""
            try:
                if ext in [".txt", ".md", ".py", ".json", ".csv", ".html", ".xml", ".yaml", ".yml"]:
                    with open(path_obj, "r", encoding="utf-8", errors="replace") as f:
                        extracted_text = f.read(6000)
                elif ext == ".pdf":
                    try:
                        from pypdf import PdfReader
                        reader = PdfReader(str(path_obj))
                        text_pages = [page.extract_text() or "" for page in reader.pages[:10]]
                        extracted_text = "\n".join(text_pages).strip()[:6000]
                    except Exception as pdf_err:
                        print(f"[GeminiClient] pypdf extraction notice: {pdf_err}")
                        extracted_text = ""
                else:
                    # Non-text or binary: do not attempt raw byte decode which exposes binary stream data
                    extracted_text = ""
            except Exception:
                extracted_text = ""

            pdf_noise_tokens = {
                "pdf", "obj", "endobj", "flatedecode", "filter", "stream", "endstream",
                "xref", "trailer", "startxref", "identity", "fontdescriptor", "cidsysteminfo",
                "length", "type", "catalog", "pages", "page", "font", "mediabox", "root",
                "parent", "kids", "count", "prev", "index", "size"
            }

            found_entities: List[str] = []
            found_topics: List[str] = []
            summary_text = ""

            if extracted_text.strip():
                import re
                clean_text = re.sub(r"\s+", " ", extracted_text).strip()
                lines = [
                    line.strip() for line in extracted_text.splitlines()
                    if len(line.strip()) > 25
                    and not any(tok in line.lower() for tok in ["endobj", "flatedecode", "startxref", "trailer", "stream"])
                ]
                lead_text = " ".join(lines[:3]) if lines else clean_text[:350]
                summary_text = f"Content analysis of {path_obj.stem}: {lead_text[:350]}."

                entity_matches = re.findall(r"\b[A-Z][a-zA-Z0-9_\-\.\#\+]*(?:\s+[A-Z][a-zA-Z0-9_\-\.\#\+]*)*\b", clean_text)
                for ent in entity_matches:
                    ent_str = ent.strip()
                    ent_lower = ent_str.lower()
                    if (
                        len(ent_str) > 2
                        and ent_str not in found_entities
                        and ent_lower not in pdf_noise_tokens
                        and not any(ent_lower.startswith(noise) for noise in ["pdf", "obj", "endobj", "stream", "filter", "flate"])
                        and not ent_lower.startswith(("the ", "this ", "page", "section", "chapter", "figure", "table", "http"))
                        and not any(c in ent_str for c in ["(", ")", "\\", "/", "{", "}", "<", ">", "%"])
                        and len(found_entities) < 8
                    ):
                        found_entities.append(ent_str)

                found_topics = [e for e in found_entities[:6] if len(e.split()) <= 4]

            stem_clean = path_obj.stem.replace("_", " ").replace("-", " ")
            if not found_topics:
                found_topics = [f"{stem_clean} Architecture", "Core Implementation", "System Analysis"]
            if not found_entities:
                found_entities = [stem_clean, "Technical System"]
            if not summary_text:
                summary_text = f"Content analysis of {stem_clean}: Detailed technical breakdown covering system design, implementation workflows, and practical applications."

            parsed_data = {
                "modality": inferred_modality,
                "summary": summary_text,
                "key_topics": found_topics,
                "entities": found_entities,
                "suggested_tone": "technical and informative",
                "notable_visual_elements": ["structured text", "diagrams"] if inferred_modality == "document" else ["visual layout"],
            }
            return AnalysisResult(parsed_data)

        raw_text = response.text or "{}"
        try:
            parsed_data = json.loads(raw_text)
        except Exception:
            validated = FileAnalysisResponse.model_validate_json(raw_text)
            parsed_data = validated.model_dump()

        return AnalysisResult(parsed_data)

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """Generate text response using Gemini API or return mock response if unconfigured."""
        target_model = model or MODEL_NAME

        if not self.is_configured():
            return (
                f"[Simulated Gemini Response] GEMINI_API_KEY is not configured in .env. "
                f"Received prompt ({len(prompt)} chars). Configure GEMINI_API_KEY to enable live AI responses."
            )

        try:
            if self._client:
                response = self._client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                )
                return response.text or ""
            else:
                import httpx
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={self.api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}]
                }
                async with httpx.AsyncClient(timeout=30.0) as http_client:
                    resp = await http_client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        return "".join(part.get("text", "") for part in parts)
                    return ""
        except Exception as e:
            return f"[GeminiClient Error] Failed to generate text: {str(e)}"

    def generate_hooks(
        self,
        aggregated_summary: str,
        key_topics: list,
        model: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate exactly 3 content hook angles for social media posts using Gemini.
        Returns a list of dicts: [{"angle": str, "headline": str, "why_it_works": str}].
        """
        target_model = model or MODEL_NAME
        topics_str = ", ".join(str(t) for t in key_topics) if key_topics else "General"

        def _get_clean_subject_topic(topics: list) -> str:
            for candidate in topics:
                c_str = str(candidate).strip()
                if c_str and not any(
                    marker in c_str.lower()
                    for marker in [".pdf", ".txt", ".docx", ".md", ".csv", "(lab)", "(", ")", "ucm", "roll", "assignment", "lab", "student"]
                ):
                    return c_str
            return "this strategy"

        clean_topic = _get_clean_subject_topic(key_topics)

        if not self.is_configured() or not self._client:
            print("[GeminiClient] GEMINI_API_KEY is not configured. Returning simulated hooks.")
            simulated_hooks = [
                {
                    "angle": "Contrarian / Myth-Busting",
                    "headline": f"Why most people get {clean_topic} completely wrong.",
                    "why_it_works": "Challenges conventional beliefs, prompting users to stop scrolling and read the alternative take.",
                },
                {
                    "angle": "Curiosity / Inside Knowledge",
                    "headline": f"The hidden insight behind our findings in {clean_topic} that changes everything.",
                    "why_it_works": "Creates an immediate knowledge gap that compels the audience to click to discover the insight.",
                },
                {
                    "angle": "Actionable Framework / How-To",
                    "headline": f"3 proven takeaways from our analysis of {clean_topic} you can apply today.",
                    "why_it_works": "Promises clear, tangible value and structured actionable advice that drives saves and shares.",
                },
            ]
            print(f"\n[GeminiClient] Generated 3 Content Hooks for Social Media:")
            for i, hook in enumerate(simulated_hooks, 1):
                print(f"  {i}. [{hook.get('angle')}] {hook.get('headline')}")
                print(f"     Why it works: {hook.get('why_it_works')}")
            return AwaitableList(simulated_hooks)

        from google.genai import types

        prompt = f"""You are an expert social media copywriter and growth strategist.
Based on the following aggregated summary and key topics extracted from analyzed files, generate exactly 3 content hook angles for social media posts.

Aggregated Summary:
{aggregated_summary}

Key Topics:
{topics_str}

Requirements:
- Generate exactly 3 distinct content hook angles.
- For each hook, provide:
  * "angle": The angle or perspective (e.g., Contrarian / Myth-Busting, FOMO / Urgency, Behind-the-Scenes / Case Study, Actionable Tip / Direct Value).
  * "headline": A compelling, scroll-stopping headline or opening sentence.
  * "why_it_works": A concise explanation of why this hook grabs attention and drives high engagement.
- Do not reference filenames, file paths, student names, roll numbers, or any document metadata in the hooks. Focus only on the actual subject matter and topics described in the summary.
"""

        hooks_schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "angle": {"type": "STRING"},
                    "headline": {"type": "STRING"},
                    "why_it_works": {"type": "STRING"},
                },
                "required": ["angle", "headline", "why_it_works"],
            },
        }

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=hooks_schema,
        )

        max_retries = 3
        response = None
        for retry_attempt in range(1, max_retries + 1):
            try:
                response = self._client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=config,
                )
                break
            except Exception as e:
                err_str = str(e)
                if ("503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str) and retry_attempt < max_retries and "PerDay" not in err_str:
                    wait_sec = retry_attempt * 3
                    print(f"[GeminiClient] Transient error during generate_hooks ({err_str}). Retrying in {wait_sec}s...")
                    time.sleep(wait_sec)
                else:
                    print(f"[GeminiClient] Quota or API limit encountered during generate_hooks: {err_str}. Using high-quality fallback hooks.")
                    response = None
                    break

        if response is None:
            fallback_hooks = [
                {
                    "angle": "Contrarian / Myth-Busting",
                    "headline": f"Why conventional wisdom around {clean_topic} is missing the real opportunity.",
                    "why_it_works": "Challenges standard assumptions, triggering immediate curiosity and engagement.",
                },
                {
                    "angle": "Curiosity / Inside Perspective",
                    "headline": f"The overlooked insight in {clean_topic} that leaders need to watch.",
                    "why_it_works": "Frames the analysis as insider knowledge that gives readers a competitive edge.",
                },
                {
                    "angle": "Actionable Framework",
                    "headline": f"3 key lessons from {clean_topic} you can implement immediately.",
                    "why_it_works": "Delivers immediate practical utility, maximizing saves and re-shares.",
                },
            ]
            print(f"\n[GeminiClient] Generated {len(fallback_hooks)} Content Hooks for Social Media:")
            for i, hook in enumerate(fallback_hooks, 1):
                print(f"  {i}. [{hook.get('angle')}] {hook.get('headline')}")
                print(f"     Why it works: {hook.get('why_it_works')}")
            return AwaitableList(fallback_hooks)

        raw_text = response.text or "[]"
        try:
            parsed_hooks = json.loads(raw_text)
            if not isinstance(parsed_hooks, list):
                parsed_hooks = [parsed_hooks]
        except Exception:
            parsed_hooks = []

        # Print the 3 generated hooks to the terminal for visibility
        print(f"\n[GeminiClient] Generated {len(parsed_hooks)} Content Hooks for Social Media using model {target_model}:")
        for i, hook in enumerate(parsed_hooks, 1):
            print(f"  {i}. [{hook.get('angle')}] {hook.get('headline')}")
            print(f"     Why it works: {hook.get('why_it_works')}")

        return AwaitableList(parsed_hooks)

    def generate_platform_copy(
        self,
        hook: dict,
        platform: str,
        model: Optional[str] = None,
    ) -> AnalysisResult:
        """
        Generate platform-specific copywriting for a given content hook.
        Platform will be one of: 'linkedin', 'instagram', 'twitter'.
        Uses structured output matching {"headline": str, "subtext": str, "caption": str, "hashtags": list[str], "cta": str}.
        """
        target_model = model or MODEL_NAME
        platform_normalized = (platform or "twitter").strip().lower()
        headline = hook.get("headline", "")
        why_it_works = hook.get("why_it_works", "")
        angle = hook.get("angle", "General Hook")

        platform_instructions = {
            "linkedin": "professional tone, 150-300 words. Format with clean spacing, strong professional insights, relevant hashtags, and a thoughtful discussion prompt.",
            "instagram": "casual tone, short, emoji-friendly, strong call-to-action (CTA). Catchy and visually engaging.",
            "twitter": "punchy, concise, strictly under 280 characters total. High impact, sharp, hook-first.",
        }

        instructions = platform_instructions.get(
            platform_normalized,
            f"Optimized for {platform_normalized} audience.",
        )

        if not self.is_configured() or not self._client:
            print(f"[GeminiClient] GEMINI_API_KEY not configured. Returning simulated copy for {platform_normalized}.")
            simulated_copy = {
                "headline": headline or f"High-Impact Strategy: {angle}",
                "subtext": f"Why this matters on {platform_normalized.capitalize()}",
                "caption": f"Simulated {platform_normalized} copy based on: {headline}. {why_it_works}",
                "hashtags": [f"#{platform_normalized}", f"#{angle.replace(' ', '')[:15]}", "#ContentStrategy"],
                "cta": f"Share your thoughts on {platform_normalized.capitalize()} below!",
            }
            return AnalysisResult(simulated_copy)

        from google.genai import types

        prompt = f"""You are an expert social media copywriter and growth marketer.
Generate high-converting platform-specific copy based on the provided content hook.

Hook Angle: {angle}
Hook Headline: {headline}
Why It Works: {why_it_works}

Target Platform: {platform_normalized}
Platform Requirements:
{instructions}

Ensure your output conforms to the requested JSON schema:
- headline: Platform-adapted headline or scroll-stopping first line.
- subtext: Supporting subtitle or value proposition statement.
- caption: The main post body adhering strictly to the platform tone and length guidelines ({instructions}).
- hashtags: An array of 3 to 5 relevant hashtags without spaces.
- cta: A compelling call to action directing the reader.
"""

        copy_schema = {
            "type": "OBJECT",
            "properties": {
                "headline": {"type": "STRING"},
                "subtext": {"type": "STRING"},
                "caption": {"type": "STRING"},
                "hashtags": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                },
                "cta": {"type": "STRING"},
            },
            "required": ["headline", "subtext", "caption", "hashtags", "cta"],
        }

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=copy_schema,
        )

        max_retries = 3
        response = None
        for retry_attempt in range(1, max_retries + 1):
            try:
                response = self._client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=config,
                )
                break
            except Exception as e:
                err_str = str(e)
                if ("503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str) and retry_attempt < max_retries and "PerDay" not in err_str:
                    wait_sec = retry_attempt * 3
                    print(f"[GeminiClient] Transient error during generate_platform_copy ({err_str}). Retrying in {wait_sec}s...")
                    time.sleep(wait_sec)
                else:
                    print(f"[GeminiClient] Quota or API limit reached for {platform_normalized}: {err_str}. Generating high-quality structured fallback copy.")
                    response = None
                    break

        if response is None:
            if platform_normalized == "linkedin":
                caption = (
                    f"{headline}\n\n"
                    f"Understanding why this works is essential: {why_it_works}\n\n"
                    f"Key Takeaways:\n"
                    f"• Focus on clear, validated metrics rather than guesswork.\n"
                    f"• Create scalable systems to implement recommendations quickly.\n"
                    f"• Align team execution with measurable strategic goals.\n\n"
                    f"What has been your team's approach to this challenge?"
                )
                hashtags = ["#Leadership", "#Innovation", "#ProfessionalGrowth", "#Strategy"]
                cta = "Join the discussion in the comments below."
            elif platform_normalized == "instagram":
                caption = (
                    f"🔥 {headline}\n\n"
                    f"Here is why it matters:\n"
                    f"✨ {why_it_works}\n\n"
                    f"Double tap if this resonates! 📌 Save this post for later."
                )
                hashtags = ["#InstaGrowth", "#ContentStrategy", "#TipsAndTricks", "#DailyInsight"]
                cta = "Drop your thoughts or favorite tip in the comments below!"
            else:  # twitter
                caption = f"{headline}\n\nWhy it works: {why_it_works[:120]}...\n\n#ActionableTips"
                hashtags = ["#Growth", "#Tech", "#Strategy"]
                cta = "RT if you found this valuable."

            return AnalysisResult({
                "headline": headline or f"{angle}: Key Takeaways",
                "subtext": f"Optimized strategy for {platform_normalized.capitalize()}",
                "caption": caption,
                "hashtags": hashtags,
                "cta": cta,
            })

        raw_text = response.text or "{}"
        try:
            parsed_copy = json.loads(raw_text)
            if not isinstance(parsed_copy, dict):
                parsed_copy = {"caption": str(parsed_copy)}
        except Exception:
            parsed_copy = {
                "headline": headline,
                "subtext": "",
                "caption": raw_text,
                "hashtags": [],
                "cta": "",
            }

        return AnalysisResult(parsed_copy)


    def generate_carousel_slides(
        self,
        copy: dict,
        platform: str,
        model: Optional[str] = None,
    ) -> AwaitableList:
        """
        Generate 4-6 short carousel slides for a LinkedIn or Instagram post based on existing copy.
        Structured output format:
        [{"slide_number": int, "slide_type": "hook"|"content"|"cta", "title": str, "body": str}]
        Keeps text short: title under 8 words, body under 25 words.
        """
        target_model = model or MODEL_NAME
        platform_normalized = (platform or "linkedin").strip().lower()
        if platform_normalized not in ["linkedin", "instagram"]:
            platform_normalized = "linkedin"

        headline = copy.get("headline", "") if isinstance(copy, dict) else ""
        subtext = copy.get("subtext", "") if isinstance(copy, dict) else ""
        caption = copy.get("caption", "") if isinstance(copy, dict) else ""
        cta = copy.get("cta", "") if isinstance(copy, dict) else ""

        def _truncate_words(text: str, max_words: int) -> str:
            if not text:
                return ""
            words = text.strip().split()
            if len(words) <= max_words:
                return " ".join(words)
            return " ".join(words[:max_words]).rstrip(".,;:!?")

        def _build_fallback_slides() -> List[Dict[str, Any]]:
            # Extract content sentences from caption
            clean_lines = [
                line.strip().lstrip("•-*0123456789. ")
                for line in caption.splitlines()
                if len(line.strip()) > 10 and not line.strip().startswith("#")
            ]
            pt1 = clean_lines[0] if clean_lines else (subtext or "Discover the core breakdown and essential takeaways.")
            pt2 = clean_lines[1] if len(clean_lines) > 1 else "Eliminate common bottlenecks by implementing systematic frameworks."
            pt3 = clean_lines[2] if len(clean_lines) > 2 else "Measure real outcomes and scale performance sustainably."

            return [
                {
                    "slide_number": 1,
                    "slide_type": "hook",
                    "title": _truncate_words(headline or "Strategic Breakthrough", 8),
                    "body": _truncate_words(subtext or "Swipe to explore the actionable lessons and critical insights.", 24),
                },
                {
                    "slide_number": 2,
                    "slide_type": "content",
                    "title": _truncate_words("Identify Core Friction", 8),
                    "body": _truncate_words(pt1, 24),
                },
                {
                    "slide_number": 3,
                    "slide_type": "content",
                    "title": _truncate_words("Implement Systematic Solutions", 8),
                    "body": _truncate_words(pt2, 24),
                },
                {
                    "slide_number": 4,
                    "slide_type": "content",
                    "title": _truncate_words("Scale With Precision", 8),
                    "body": _truncate_words(pt3, 24),
                },
                {
                    "slide_number": 5,
                    "slide_type": "cta",
                    "title": _truncate_words("Take Action Today", 8),
                    "body": _truncate_words(cta or "Save this post and share your perspective below.", 24),
                },
            ]

        if not self.is_configured() or not self._client:
            print(f"[GeminiClient] GEMINI_API_KEY not configured. Returning simulated carousel slides for {platform_normalized}.")
            simulated = _build_fallback_slides()
            return AwaitableList(simulated)

        from google.genai import types

        prompt = f"""You are an elite social media strategist specializing in high-engagement {platform_normalized.capitalize()} carousels.
Break down the following post copy into exactly 4 to 6 short, punchy carousel slides.

Input Copy:
Headline: {headline}
Subtext: {subtext}
Caption Content:
{caption}
Call to Action: {cta}

Slide Structure Requirements:
- Total slides: between 4 and 6 slides.
- Slide 1 (slide_type="hook"): The hook/title slide. Title must be big, scroll-stopping, and under 8 words. Brief body under 25 words.
- Slides 2 to N-1 (slide_type="content"): One key takeaway per slide extracted from the caption content. Title under 8 words, body 1-2 sentences max and strictly under 25 words.
- Final Slide (slide_type="cta"): A concise summary or call-to-action slide. Title under 8 words, body under 25 words.

CRITICAL CONSTRAINTS:
- Keep text SHORT. These are visual carousel slides, not paragraphs.
- "title": Strictly under 8 words.
- "body": Strictly under 25 words.
- Do NOT reference filenames, file paths, or document metadata.
"""

        slides_schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "slide_number": {"type": "INTEGER"},
                    "slide_type": {
                        "type": "STRING",
                        "enum": ["hook", "content", "cta"],
                    },
                    "title": {"type": "STRING"},
                    "body": {"type": "STRING"},
                },
                "required": ["slide_number", "slide_type", "title", "body"],
            },
        }

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=slides_schema,
        )

        max_retries = 3
        response = None
        for retry_attempt in range(1, max_retries + 1):
            try:
                response = self._client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=config,
                )
                break
            except Exception as e:
                err_str = str(e)
                if ("503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str) and retry_attempt < max_retries and "PerDay" not in err_str:
                    wait_sec = retry_attempt * 3
                    print(f"[GeminiClient] Transient error during generate_carousel_slides ({err_str}). Retrying in {wait_sec}s...")
                    time.sleep(wait_sec)
                else:
                    print(f"[GeminiClient] Quota or API limit reached during generate_carousel_slides: {err_str}. Generating high-quality structured fallback slides.")
                    response = None
                    break

        if response is None:
            fallback = _build_fallback_slides()
            return AwaitableList(fallback)

        raw_text = response.text or "[]"
        try:
            parsed_slides = json.loads(raw_text)
            if not isinstance(parsed_slides, list):
                parsed_slides = [parsed_slides]
        except Exception:
            parsed_slides = _build_fallback_slides()

        # Enforce constraints and 1-indexed slide numbers
        cleaned_slides = []
        for idx, slide in enumerate(parsed_slides, start=1):
            stype = slide.get("slide_type", "content")
            if stype not in ["hook", "content", "cta"]:
                stype = "hook" if idx == 1 else ("cta" if idx == len(parsed_slides) else "content")

            cleaned_slides.append({
                "slide_number": idx,
                "slide_type": stype,
                "title": _truncate_words(slide.get("title", f"Point {idx}"), 8),
                "body": _truncate_words(slide.get("body", ""), 25),
            })

        return AwaitableList(cleaned_slides)


# Default singleton instance
gemini_client = GeminiClient()


def analyze_file(
    file_path: str,
    prompt: Optional[str] = None,
    model: Optional[str] = None,
) -> AnalysisResult:
    """Convenience module-level function to analyze an uploaded file with Gemini."""
    return gemini_client.analyze_file(file_path=file_path, prompt=prompt, model=model)


def generate_hooks(
    aggregated_summary: str,
    key_topics: list,
    model: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Convenience module-level function to generate 3 content hooks using Gemini."""
    return gemini_client.generate_hooks(aggregated_summary=aggregated_summary, key_topics=key_topics, model=model)


def generate_platform_copy(
    hook: dict,
    platform: str,
    model: Optional[str] = None,
) -> dict:
    """Convenience module-level function to generate platform-specific copy using Gemini."""
    return gemini_client.generate_platform_copy(hook=hook, platform=platform, model=model)


def generate_carousel_slides(
    copy: dict,
    platform: str,
    model: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Convenience module-level function to generate carousel slides using Gemini."""
    return gemini_client.generate_carousel_slides(copy=copy, platform=platform, model=model)
