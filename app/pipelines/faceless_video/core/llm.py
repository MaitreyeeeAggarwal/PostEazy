from __future__ import annotations

import json
import os
import re
import requests
from pathlib import Path
from typing import Any, Type, TypeVar, Optional
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

# Load .env file automatically if present
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.is_file():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip("'\"")

NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
DEFAULT_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.2-11b-vision-instruct")
FAST_MODEL = os.getenv("NVIDIA_FAST_MODEL", "meta/llama-3.2-11b-vision-instruct")

class NVIDIAClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = NVIDIA_BASE_URL, default_model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY") or os.getenv("NVAPI_KEY")
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def complete(self, prompt: str, system_prompt: str = "", model: Optional[str] = None, temperature: float = 0.2, max_tokens: int = 2048, timeout: float = 120.0) -> str:
        """Calls NVIDIA OpenAI-compatible chat completions endpoint with automatic retries for timeouts."""
        if not self.is_configured:
            raise ValueError("NVIDIA_API_KEY environment variable is not set.")

        chosen_model = model or self.default_model
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": chosen_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        last_err = None
        for attempt in range(3):
            try:
                resp = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=timeout)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except (requests.exceptions.Timeout, requests.exceptions.HTTPError) as err:
                last_err = err
                print(f"[NVIDIA Client] API call attempt {attempt + 1}/3 failed ({err}). Retrying...")
                import time
                time.sleep(2 * (attempt + 1))
        
        raise last_err or RuntimeError("NVIDIA API call failed after retries.")

    def complete_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_retries: int = 3
    ) -> T:
        """Calls NVIDIA LLM and parses response into a Pydantic model with retry logic."""
        schema_dict = response_schema.model_json_schema()
        top_keys = list(schema_dict.get("properties", {}).keys())
        schema_json = json.dumps(schema_dict, indent=2)
        
        augmented_system = (
            f"{system_prompt}\n\n"
            f"CRITICAL: You MUST respond ONLY with a single valid JSON object with the fields: {top_keys}.\n"
            f"Do NOT output schema definitions, '$defs', or wrapper objects.\n\n"
            f"JSON SCHEMA:\n{schema_json}\n\n"
            f"Return ONLY JSON surrounded by ```json ... ``` blocks or raw JSON string."
        )

        current_prompt = prompt
        for attempt in range(max_retries):
            try:
                raw_response = self.complete(current_prompt, system_prompt=augmented_system, model=model, temperature=temperature)
                json_str = self._extract_json(raw_response)
                parsed_dict = json.loads(json_str)
                if isinstance(parsed_dict, dict):
                    parsed_dict = self._unwrap_dict(parsed_dict, top_keys)
                return response_schema.model_validate(parsed_dict)
            except (json.JSONDecodeError, ValidationError, ValueError) as e:
                if attempt == max_retries - 1:
                    raise e
                # Append error message for repair attempt
                current_prompt = f"{prompt}\n\n[Previous attempt failed with error]: {str(e)}\nPlease fix the format and strictly output valid JSON with top-level keys {top_keys}."

        raise RuntimeError("Failed to generate structured response after retries.")

    def _unwrap_dict(self, data: dict, top_keys: list[str]) -> dict:
        """Recursively unwraps dictionary if top_keys are nested inside a sub-key."""
        if not isinstance(data, dict):
            return data
        if any(k in data for k in top_keys):
            return data
        for k, v in data.items():
            if isinstance(v, dict):
                unwrapped = self._unwrap_dict(v, top_keys)
                if any(key in unwrapped for key in top_keys):
                    return unwrapped
        return data

    def _extract_json(self, text: str) -> str:
        """Extracts JSON substring from markdown code blocks or raw text."""
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        text = text.strip()
        start_idx = min((text.find(c) for c in ("{", "[") if text.find(c) != -1), default=0)
        end_idx = max((text.rfind(c) for c in ("}", "]") if text.rfind(c) != -1), default=len(text) - 1)
        return text[start_idx : end_idx + 1]


def get_llm_client() -> NVIDIAClient:
    """Returns an instance of NVIDIAClient."""
    return NVIDIAClient()
