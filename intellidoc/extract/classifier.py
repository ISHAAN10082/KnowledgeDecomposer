from intellidoc.config import settings
from intellidoc.models.ollama_client import OllamaClient
from intellidoc.models.prompts import DOCUMENT_CLASSIFICATION_PROMPT

class DocumentClassifier:
    """Classifies documents into predefined categories."""
    def __init__(self):
        self.model = OllamaClient(settings.models.validation_model)
        self.cache = {}

    def classify(self, document_id: str, text: str) -> str:
        """Classifies document content into a category."""
        if document_id in self.cache:
            return self.cache[document_id]
            
        sample = text[:2000]
        prompt = DOCUMENT_CLASSIFICATION_PROMPT.format(text_sample=sample)
        
        # We expect a single-word response: invoice, resume, or other
        category = self.model.generate(prompt).strip().lower()
        
        # Basic validation
        if category not in ["invoice", "resume", "other"]:
            category = "other"
            
        self.cache[document_id] = category
        return category 