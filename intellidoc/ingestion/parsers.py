import os
import mimetypes
from pathlib import Path
from typing import Optional

import pymupdf
import pandas as pd
from docx import Document as DocxDocument
import markdown
import cv2
import easyocr
import numpy as np

from intellidoc.preprocessing.image_utils import preprocess_image

# Initialize the OCR reader once to avoid reloading the model
# Using ['en'] for English, and gpu=True will automatically use CUDA or MPS if available
ocr_reader = easyocr.Reader(['en'], gpu=True)

def read_image_with_ocr(path: str) -> str:
    """Reads an image, preprocesses it, and extracts text using OCR."""
    try:
        # Preprocess the image to improve OCR accuracy
        processed_image_np = preprocess_image(path)
        
        # Use EasyOCR to extract text
        # detail=0 means we only want the extracted text, not bounding boxes
        result = ocr_reader.readtext(processed_image_np, detail=0, paragraph=True)
        
        return "\n".join(result)
    except Exception as e:
        print(f"Error processing image {path} with OCR: {e}")
        return ""

def read_pdf_streaming(path: str, max_pages: int = 50) -> str:
    """
    Read PDF with page limits. Tries to extract text directly,
    falls back to OCR if the document appears to be scanned.
    """
    try:
        doc = pymupdf.open(path)
        total_pages = len(doc)
        pages_to_read = min(max_pages, total_pages)
        
        print(f"PDF has {total_pages} pages, processing first {pages_to_read} pages")
        
        text_parts = []
        is_scanned = False
        
        # First pass: try to extract text directly
        for page_num in range(pages_to_read):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                text_parts.append(text)
        
        full_text = "\n\n".join(text_parts)

        # If direct text extraction yields very little, assume it's a scanned PDF
        if len(full_text.strip()) < 100 * pages_to_read:
            print(f"PDF {path} appears to be scanned. Falling back to OCR.")
            is_scanned = True
            text_parts = [] # Reset text parts for OCR
        
        if is_scanned:
            for page_num in range(pages_to_read):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=300) # Render page as a high-DPI image
                img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                
                # Convert to BGR for OpenCV
                if pix.n == 4: # RGBA
                    img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
                elif pix.n == 1: # Grayscale
                    img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)

                # Use EasyOCR on the image buffer
                result = ocr_reader.readtext(img_np, detail=0, paragraph=True)
                text_parts.append("\n".join(result))
        
        doc.close()
        
        final_text = "\n\n--- Page Break ---\n\n".join(text_parts)
        
        # Additional safety check
        if len(final_text) > 1_000_000:  # 1MB text limit
            print(f"Text too long ({len(final_text)} chars), truncating to 1MB")
            final_text = final_text[:1_000_000]
            
        return final_text
        
    except Exception as e:
        print(f"Error reading PDF {path}: {e}")
        return ""

def read_txt(path: str) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Limit text file size
            if len(content) > 1_000_000:
                content = content[:1_000_000]
            return content
    except Exception as e:
        print(f"Error reading text file {path}: {e}")
        return ""

def read_md(path: str) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Limit markdown file size
            if len(content) > 1_000_000:
                content = content[:1_000_000]
            return markdown.markdown(content)
    except Exception as e:
        print(f"Error reading markdown file {path}: {e}")
        return ""

def read_csv(path: str) -> str:
    try:
        # Read only first 1000 rows to prevent memory issues
        df = pd.read_csv(path, nrows=1000)
        return df.to_string(max_rows=100)  # Limit output
    except Exception as e:
        print(f"Error reading CSV file {path}: {e}")
        return ""

def read_docx(path: str) -> str:
    try:
        doc = DocxDocument(path)
        text_parts = []
        char_count = 0
        
        for paragraph in doc.paragraphs:
            if char_count > 1_000_000:  # 1MB limit
                break
            text = paragraph.text.strip()
            if text:
                text_parts.append(text)
                char_count += len(text)
                
        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"Error reading DOCX file {path}: {e}")
        return ""

def read_any(path: str) -> Optional[str]:
    """Read any supported file type with memory safety."""
    if not os.path.exists(path):
        return None
        
    file_size = os.path.getsize(path)
    if file_size > 50 * 1024 * 1024:  # 50MB limit
        print(f"File {path} too large ({file_size / 1024 / 1024:.1f}MB), skipping")
        return None
    
    ext = Path(path).suffix.lower()
    
    readers = {
        '.pdf': read_pdf_streaming,
        '.txt': read_txt,
        '.md': read_md,
        '.csv': read_csv,
        '.docx': read_docx,
        '.png': read_image_with_ocr,
        '.jpg': read_image_with_ocr,
        '.jpeg': read_image_with_ocr,
    }
    
    reader = readers.get(ext)
    if reader:
        return reader(path)
    
    print(f"Unsupported file type: {ext}")
    return None 