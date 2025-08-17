import json
import networkx as nx
from typing import List

from localknow.types import Concept, Principle, Controversy

class HierarchicalKnowledgeBuilder:
    def __init__(self):
        self.G = nx.DiGraph()

    def add_concepts(self, concepts: List[Concept], doc_id: str):
        for c in concepts:
            self.G.add_node(
                c.name,
                type="concept",
                confidence=c.confidence,
                description=c.description,
                doc_id=doc_id
            )

    def add_principles(self, principles: List[Principle], doc_id: str):
        for p in principles:
            self.G.add_node(
                p.name,
                type="principle",
                confidence=p.confidence,
                rationale=p.rationale,
                doc_id=doc_id
            )

    def add_controversies(self, controversies: List[Controversy], doc_id: str):
        for c in controversies:
            self.G.add_node(
                c.topic,
                type="controversy",
                confidence=c.confidence,
                viewpoints=json.dumps(c.viewpoints),
                doc_id=doc_id
            )

    def map_dependencies(self, concepts: List[Concept], principles: List[Principle]):
        """Creates edges between principles and the concepts they underpin."""
        principle_names = {p.name for p in principles}
        for concept in concepts:
            # Simple heuristic: link concept to a principle if its name is in the rationale.
            for principle in principles:
                if concept.name.lower() in principle.rationale.lower():
                    self.G.add_edge(principle.name, concept.name, rel="explains")

    def to_networkx(self) -> nx.DiGraph:
        return self.G

    def to_json(self) -> str:
        """Serializes the graph to a JSON format for APIs."""
        return json.dumps(nx.node_link_data(self.G), indent=2) 