import json
from typing import List

from localknow.config import settings
from localknow.models.ollama_client import OllamaClient
from localknow.types import Controversy, Concept
from localknow.models.prompts import CONTROVERSY_DETECTION_PROMPT


class ControversyDetector:
    def __init__(self):
        # Using a powerful reasoning model is best for this task
        self.debate_model = OllamaClient(settings.models.reasoning_model)

    def identify_debates(self, concepts: List[Concept], text: str) -> List[Controversy]:
        """Identifies controversies and debates within the text."""
        if not concepts:
            return []

        concept_names = ", ".join([f'"{c.name}"' for c in concepts])
        text_sample = text[:8000]

        prompt = CONTROVERSY_DETECTION_PROMPT.format(
            concepts=concept_names,
            text_sample=text_sample
        )

        response = self.debate_model.generate(prompt)
        try:
            data = json.loads(response)
            controversies = [
                Controversy(
                    topic=c.get("topic", "").strip(),
                    viewpoints=c.get("viewpoints", []),
                    confidence=float(c.get("confidence", 0.5))
                )
                for c in data if c.get("topic") and c.get("viewpoints")
            ]
            return controversies
        except (json.JSONDecodeError, TypeError):
            return [] 