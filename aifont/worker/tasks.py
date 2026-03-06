"""Celery tasks for async font processing."""

from aifont.worker.celery_app import celery_app


@celery_app.task(name="aifont.worker.tasks.analyze_font")
def analyze_font(font_path: str) -> dict:
    """Analyze a font file and return a report."""
    return {"status": "pending", "font_path": font_path}


@celery_app.task(name="aifont.worker.tasks.generate_font")
def generate_font(prompt: str, output_path: str) -> dict:
    """Generate a font from a natural language prompt."""
    return {"status": "pending", "prompt": prompt, "output_path": output_path}
