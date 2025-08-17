from typing import List
import numpy as np

from localknow.types import Concept, QualityReport

class ValidationEngine:
    """Provides quality assurance by scoring extracted information."""

    def calculate_quality(self, concepts: List[Concept]) -> QualityReport:
        """Calculates a quality score based on the confidence of extracted concepts."""
        if not concepts:
            return QualityReport(avg_concept_confidence=0.0, low_confidence_concepts=[])

        confidences = [c.confidence for c in concepts]
        avg_confidence = float(np.mean(confidences))

        # Flag concepts with confidence below a certain threshold (e.g., 0.6)
        low_confidence_concepts = [c for c in concepts if c.confidence < 0.6]

        return QualityReport(
            avg_concept_confidence=round(avg_confidence, 3),
            low_confidence_concepts=low_confidence_concepts
        ) 