import os
from typing import Any, Dict, List
from services.gemini_client import GeminiClient, gemini_client


class GeneratorService:
    """Service to orchestrate generation tasks using parsed file contents and Gemini."""

    def __init__(self, client: GeminiClient = gemini_client):
        self.client = client

    async def generate_summary_and_analysis(
        self,
        job_id: str,
        parsed_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze all uploaded files using Gemini Files API and compile structured results."""
        file_analyses = []

        for file_info in parsed_files:
            file_path = file_info.get("file_path")
            if file_path and os.path.exists(file_path):
                # Call analyze_file to upload actual file bytes to Gemini Files API
                analysis = await self.client.analyze_file(file_path=file_path)
                file_analyses.append({
                    "filename": file_info.get("filename"),
                    "file_path": file_path,
                    "analysis": analysis,
                })

        return {
            "job_id": job_id,
            "processed_file_count": len(parsed_files),
            "summary": f"Analyzed {len(file_analyses)} file(s) successfully using Gemini Files API.",
            "file_analyses": file_analyses,
            "metadata": {
                "gemini_enabled": self.client.is_configured(),
            },
        }


# Default singleton instance
generator_service = GeneratorService()
