import json
from typing import List

from localknow.config import settings
from localknow.models.ollama_client import OllamaClient
from localknow.types import Concept
from localknow.models.prompts import CONCEPT_EXTRACTION_PROMPT


class RobustConceptExtractor:
    def __init__(self):
        self.primary = OllamaClient(settings.models.primary_model)
        self.validation = OllamaClient(settings.models.validation_model)

    def _extract(self, text: str, client: OllamaClient) -> List[Concept]:
        resp = client.generate(CONCEPT_EXTRACTION_PROMPT.replace("{TEXT}", text) + "\nJSON:")
        try:
            data = json.loads(resp)
        except Exception:
            data = []
        concepts: List[Concept] = []
        for c in data:
            try:
                concepts.append(
                    Concept(
                        name=str(c.get("name", "")).strip(),
                        description=str(c.get("description", "")).strip(),
                        confidence=float(c.get("confidence", 0.5)),
                        sources=[],
                    )
                )
            except Exception:
                continue
        return concepts

    def extract_with_validation(self, text: str) -> List[Concept]:
        c1 = self._extract(text, self.primary)
        c2 = self._extract(text, self.validation)
        # Simple consensus: union; if both present, average confidence
        by_name = {}
        for c in c1 + c2:
            key = c.name.lower()
            if not key:
                continue
            if key not in by_name:
                by_name[key] = c
            else:
                by_name[key].confidence = min(1.0, (by_name[key].confidence + c.confidence) / 2.0)
        return list(by_name.values()) 