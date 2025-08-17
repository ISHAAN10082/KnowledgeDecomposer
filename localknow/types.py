from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class Document:
    document_id: str
    path: str
    content: str
    metadata: Dict[str, Any]


@dataclass
class Concept:
    name: str
    description: str
    confidence: float
    sources: List[str]


@dataclass
class Principle:
    name: str
    rationale: str
    confidence: float


@dataclass
class Controversy:
    topic: str
    viewpoints: List[str]
    confidence: float


@dataclass
class QualityReport:
    avg_concept_confidence: float
    low_confidence_concepts: List[Concept]


@dataclass
class ProcessingDecision:
    path: str
    action: str  # full|limited|skip
    reason: Optional[str] = None


@dataclass
class ProcessingPlan:
    decisions: List[ProcessingDecision]

    def add_full_processing(self, doc_path: str) -> None:
        self.decisions.append(ProcessingDecision(path=doc_path, action="full"))

    def add_limited_processing(self, doc_path: str) -> None:
        self.decisions.append(ProcessingDecision(path=doc_path, action="limited"))

    def add_skip_processing(self, doc_path: str, reason: str) -> None:
        self.decisions.append(ProcessingDecision(path=doc_path, action="skip", reason=reason)) 