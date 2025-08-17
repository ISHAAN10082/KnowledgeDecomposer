import json
from typing import Type, TypeVar, Optional
from pydantic import BaseModel, ValidationError

from intellidoc.config import settings
from intellidoc.models.ollama_client import OllamaClient
from intellidoc.utils.helpers import robust_json_load
from intellidoc.extract.schemas import ExtractionResult

# Create a generic type variable for Pydantic models
T = TypeVar("T", bound=BaseModel)

class StructuredDataExtractor:
    def __init__(self, max_retries: int = 2):
        # Use a model that supports vision, like LLaVA
        self.model = OllamaClient(settings.models.primary_model) 
        self.max_retries = max_retries

    def _generate_prompt(self, text: Optional[str], schema: Type[T], image_provided: bool) -> str:
        """Generates a prompt for the LLM to extract data based on the schema."""
        schema_json = json.dumps(schema.schema(), indent=2)
        
        # We now wrap the target schema inside the ExtractionResult schema
        wrapper_schema = json.dumps(ExtractionResult.schema(), indent=2)

        if image_provided:
            # Vision-specific prompt
            prompt_intro = (
                "You are an expert data extractor analyzing a document image. "
                "Your task is to extract structured data from the image based on the "
                "target schema, and then wrap it in the provided result schema. "
                "The provided text is an OCR transcript of the image; use it to improve accuracy, "
                "but trust the visual information in the image first. For justifications, briefly "
                "describe the location of the data on the page (e.g., 'top right corner'). "
                "Respond with ONLY the JSON object that matches the result schema."
            )
        else:
            # Text-only prompt
            prompt_intro = (
                "You are an expert data extractor. Your task is to extract structured data "
                "from the provided text based on the target schema, and then wrap it in the "
                "provided result schema. For justifications, briefly quote the text "
                "that supports the extracted value. Respond with ONLY the JSON object that "
                "matches the result schema."
            )

        prompt = (
            f"{prompt_intro}\n\n"
            f"Result Schema:\n---\n{wrapper_schema}\n---\n\n"
            f"Target Data Schema (to be placed inside 'extracted_data' field):\n---\n{schema_json}\n---\n\n"
        )
        if text:
             prompt += f"Text:\n---\n{text}\n---\n\n"
        
        prompt += "JSON Output:"
        return prompt

    def extract(self, text: str, schema: Type[T], image_path: Optional[str] = None) -> ExtractionResult:
        """
        Extracts structured data, with a validation and self-correction loop.
        Uses vision if an image_path is provided.
        """
        prompt = self._generate_prompt(text, schema, image_provided=(image_path is not None))
        
        for attempt in range(self.max_retries + 1):
            if image_path:
                response_text = self.model.generate_with_image(prompt, image_path)
            else:
                response_text = self.model.generate(prompt)

            json_data = robust_json_load(response_text)
            
            if json_data is None:
                if attempt < self.max_retries:
                    prompt += f"\n\nPrevious attempt failed. The output was not valid JSON. Please try again, ensuring the output is a single, valid JSON object that conforms to the Result Schema."
                    continue
                else:
                    raise ValueError("Failed to extract valid JSON after multiple retries.")

            try:
                # We now parse into the wrapper ExtractionResult schema
                validated_data = ExtractionResult.parse_obj(json_data)
                # And then we validate the inner data against the target schema
                schema.parse_obj(validated_data.extracted_data)
                return validated_data
            except ValidationError as e:
                if attempt < self.max_retries:
                    error_str = str(e)
                    prompt += f"\n\nPrevious attempt failed validation with the following errors:\n{error_str}\nPlease re-examine the document, target schema, and result schema, then provide a corrected JSON object.\n\nJSON Output:"
                    continue
                else:
                    raise e # Raise the final validation error after all retries failed

        raise ValueError("Extraction failed after all retries.") 