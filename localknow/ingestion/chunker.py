from typing import List, Tuple, Optional
import re

class TextChunker:
    def __init__(self, base_chunk_size: int = 2000, chunk_overlap: int = 100):  # Reduced from 4000/200
        self.base_chunk_size = base_chunk_size
        self.chunk_overlap = chunk_overlap
        self.sentence_end_pattern = re.compile(r'[.!?]\s+')
        self.paragraph_pattern = re.compile(r'\n\s*\n')

    def _find_better_boundary(self, text: str, position: int, window: int = 50) -> int:
        """Find a natural boundary near the target position."""
        start = max(0, position - window)
        end = min(len(text), position + window)
        search_region = text[start:end]
        
        # Look for paragraph breaks first
        paragraph_breaks = list(self.paragraph_pattern.finditer(search_region))
        if paragraph_breaks:
            # Choose the closest paragraph break
            best_break = min(paragraph_breaks, key=lambda m: abs(m.start() - (position - start)))
            return start + best_break.start()
        
        # Look for sentence endings
        sentence_endings = list(self.sentence_end_pattern.finditer(search_region))
        if sentence_endings:
            # Choose the closest sentence ending
            best_ending = min(sentence_endings, key=lambda m: abs(m.start() - (position - start)))
            return start + best_ending.end()
        
        # Fall back to the original position
        return position

    def chunk(self, text: str) -> List[str]:
        """Split text into overlapping chunks with natural boundaries."""
        if len(text) <= self.base_chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.base_chunk_size
            
            if end >= len(text):
                # Last chunk
                chunks.append(text[start:])
                break
            
            # Find a better boundary
            actual_end = self._find_better_boundary(text, end)
            
            chunk = text[start:actual_end]
            chunks.append(chunk)
            
            # Calculate next start position with overlap
            start = actual_end - self.chunk_overlap
            
            # Safety check to prevent infinite loops
            if len(chunks) > 1 and start <= len(chunks[-1]):  # If we're not making progress
                start = actual_end
        
        return chunks

    def chunk_with_metadata(self, text: str, document_id: str) -> List[Tuple[str, dict]]:
        """Chunk text and return with metadata."""
        chunks = self.chunk(text)
        result = []
        
        for i, chunk in enumerate(chunks):
            metadata = {
                "document_id": document_id,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunk_size": len(chunk)
            }
            result.append((chunk, metadata))
        
        return result
    
    def get_optimal_chunk_size(self, text_sample: str) -> int:
        """Determine optimal chunk size based on content complexity."""
        # Count mathematical formulas, equations, code blocks
        formula_density = len(re.findall(r'[\$\\\[\]]|\\[a-zA-Z]+', text_sample)) / len(text_sample)
        
        if formula_density > 0.1:  # High formula density
            return max(1000, self.base_chunk_size // 3)  # Smaller chunks for complex content
        elif formula_density > 0.05:  # Medium formula density
            return max(1500, self.base_chunk_size // 2)
        else:
            return self.base_chunk_size 