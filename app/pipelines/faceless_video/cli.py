import sys
import click
from orchestrator import PipelineOrchestrator


@click.group()
def cli():
    """doc2video CLI: Dense documents in, faceless kinetic typography video out."""
    pass


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--target-seconds", "-t", default=60.0, help="Target video duration in seconds (default: 60s).")
@click.option("--preset", "-p", default="shorts", type=click.Choice(["reels", "shorts", "tiktok", "youtube", "linkedin"]), help="Platform video export preset.")
@click.option("--draft", is_flag=True, help="Fast 24fps draft render mode.")
@click.option("--review", is_flag=True, help="Pause after Stage 4 to inspect and hand-edit scenes.json.")
def run(input_file: str, target_seconds: float, preset: str, draft: bool, review: bool):
    """Run the 8-stage video generation pipeline on an input document file (.pptx, .pdf, .docx, .md, .txt)."""
    orchestrator = PipelineOrchestrator(draft_mode=draft)
    try:
        res = orchestrator.run_pipeline(
            input_file=input_file,
            target_seconds=target_seconds,
            preset=preset,
            review_pause=review
        )
        print(f"\nPipeline result: {res}")
    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli()
