import os
import mimetypes
from pathlib import Path
from typing import Optional

import pymupdf
import pandas as pd
from docx import Document as DocxDocument
import markdown

def read_pdf_streaming(path: str, max_pages: int = 50) -> str:
    """Read PDF with page limits to prevent memory exhaustion."""
    try:
        doc = pymupdf.open(path)
        total_pages = len(doc)
        
        # Limit pages to prevent memory issues
        pages_to_read = min(max_pages, total_pages)
        
        print(f"PDF has {total_pages} pages, reading first {pages_to_read} pages")
        
        text_parts = []
        for page_num in range(pages_to_read):
            try:
                page = doc[page_num]
                text = page.get_text()
                if text.strip():  # Only add non-empty pages
                    text_parts.append(text)
            except Exception as e:
                print(f"Error reading page {page_num}: {e}")
                continue
        
        doc.close()
        
        full_text = "\n\n".join(text_parts)
        
        # Additional safety check
        if len(full_text) > 1_000_000:  # 1MB text limit
            print(f"Text too long ({len(full_text)} chars), truncating to 1MB")
            full_text = full_text[:1_000_000]
            
        return full_text
        
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
    }
    
    reader = readers.get(ext)
    if reader:
        return reader(path)
    
    print(f"Unsupported file type: {ext}")
    return None 