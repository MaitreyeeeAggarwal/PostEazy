import re
from app.core.ir import Claim, Block, DocIR


NUMERIC_PATTERN = re.compile(r"(\b\d+(\.\d+)?%?|\$\d+|\b\d+\s*(percent|billion|million|k)\b)", re.IGNORECASE)


def compute_salience(claim_text: str, source_block: Block, model_rating: float = 0.5) -> float:
    """Blends four signals to produce a 0-1 salience score for a claim."""
    score = 0.0

    # 1. Contains numbers, percentages, or figures (+0.30)
    if NUMERIC_PATTERN.search(claim_text):
        score += 0.30

    # 2. Heading-level origin (+0.20)
    if source_block.level <= 1:
        score += 0.20

    # 3. High impact claim kinds (+0.20)
    # Checked upstream in claim creation

    # 4. Model's subjective rating (+0.30)
    score += max(0.0, min(1.0, model_rating)) * 0.30

    return min(1.0, round(score, 3))
