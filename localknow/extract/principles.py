import json
from typing import List

from localknow.config import settings
from localknow.models.ollama_client import OllamaClient
from localknow.types import Principle, Concept
from localknow.models.prompts import PRINCIPLE_EXTRACTION_PROMPT


class FirstPrinciplesExtractor:
    def __init__(self):
        self.reasoning_model = OllamaClient(settings.models.reasoning_model)

    def extract_foundational_truths(self, concepts: List[Concept], text: str) -> List[Principle]:
        """Extracts first principles from text using a list of concepts as context."""
        if not concepts:
            return []

        concept_names = ", ".join([f'"{c.name}"' for c in concepts])
        text_sample = text[:8000]  # Use a larger sample for reasoning

        prompt = PRINCIPLE_EXTRACTION_PROMPT.format(
            concepts=concept_names,
            text_sample=text_sample
        )

        response = self.reasoning_model.generate(prompt)
        try:
            data = json.loads(response)
            principles = [
                Principle(
                    name=p.get("name", "").strip(),
                    rationale=p.get("rationale", "").strip(),
                    confidence=float(p.get("confidence", 0.5))
                )
                for p in data if p.get("name")
            ]
            return principles
        except (json.JSONDecodeError, TypeError):
            return [] 