import argparse
import os
import uuid
import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

from intellidoc.config import settings
from intellidoc.core.validators import ContentValidator
from intellidoc.core.domain_guardian import ResourceGuardian
from intellidoc.ingestion.parsers import read_any
from intellidoc.persist.versioning import VersionTracker
from intellidoc.types import Document
from intellidoc.dedup.deduplicator import AdvancedContentDeduplicator
from intellidoc.extract.classifier import DocumentClassifier
from intellidoc.extract.extractor import StructuredDataExtractor
from intellidoc.extract.schemas import Invoice


def build_documents(paths: List[str]) -> List[Document]:
    docs: List[Document] = []
    for p in paths:
        content = read_any(p)
        if content:
            docs.append(
                Document(
                    document_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, p)),
                    path=p,
                    content=content,
                    metadata={"path": p},
                )
            )
    return docs

def process_document_path(path: str) -> Dict[str, Any]:
    """Helper function to process a single document from its path."""
    doc = build_documents([path])[0]
    return process_single_document(doc)

def process_single_document(doc: Document) -> Dict[str, Any]:
    """Orchestrates the classification and extraction for a single document."""
    try:
        # Initialize services
        classifier = DocumentClassifier()
        extractor = StructuredDataExtractor()

        # 1. Classify the document
        doc_type = classifier.classify(doc.document_id, doc.content)
        print(f"Document {doc.path} classified as: {doc_type}")

        # 2. Extract structured data based on type
        extracted_data = None
        if doc_type == "invoice":
            try:
                # Pass the original file path for vision-enabled extraction
                extraction_result = extractor.extract(doc.content, Invoice, image_path=doc.path)
                extracted_data = extraction_result.dict() if extraction_result else None
                print(f"Successfully extracted invoice data from {doc.path}")
            except Exception as e:
                print(f"Failed to extract invoice data from {doc.path}: {e}")
                return {"status": "error", "reason": str(e), "doc_id": doc.document_id, "path": doc.path}

        return {
            "status": "success",
            "doc_id": doc.document_id,
            "path": doc.path,
            "doc_type": doc_type,
            "extracted_data": extracted_data,
        }
    except Exception as e:
        print(f"Error processing {doc.path}: {e}")
        return {"status": "error", "reason": str(e), "doc_id": doc.document_id, "path": doc.path, "content": ""}


class CheckpointManager:
    """Manages checkpoints for resumable processing."""
    
    def __init__(self, input_dir: str):
        self.checkpoint_dir = Path(".intellidoc/checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = self.checkpoint_dir / f"{self._hash_path(input_dir)}.checkpoint"
        
    def _hash_path(self, path: str) -> str:
        """Create a safe filename from a path."""
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, path))
        
    def save_checkpoint(self, processed_paths: Set[str], results: Dict[str, Any]) -> None:
        """Save current processing state."""
        checkpoint_data = {
            "processed_paths": list(processed_paths),
            "results": results
        }
        with open(self.checkpoint_file, 'wb') as f:
            pickle.dump(checkpoint_data, f)
        print(f"Checkpoint saved: {len(processed_paths)} documents processed so far")
            
    def load_checkpoint(self) -> Dict[str, Any]:
        """Load previous processing state if exists."""
        if not self.checkpoint_file.exists():
            return {"processed_paths": set(), "results": {}}
            
        try:
            with open(self.checkpoint_file, 'rb') as f:
                data = pickle.load(f)
                data["processed_paths"] = set(data["processed_paths"])
                print(f"Resuming from checkpoint: {len(data['processed_paths'])} documents already processed")
                return data
        except Exception as e:
            print(f"Error loading checkpoint: {e}")
            return {"processed_paths": set(), "results": {}}
            
    def clear_checkpoint(self) -> None:
        """Remove checkpoint after successful completion."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()


def main(input_dir: str) -> Dict[str, Any]:
    # Setup checkpoint manager for resumability
    checkpoint_mgr = CheckpointManager(input_dir)
    checkpoint = checkpoint_mgr.load_checkpoint()
    processed_paths = checkpoint["processed_paths"]
    summary = checkpoint["results"].get("summary", {"processed": 0, "successful_extractions": 0})
    
    # 1. Initialization
    validator = ContentValidator()
    guardian = ResourceGuardian()
    vt = VersionTracker(settings.sqlite_db_path)
    dedup = AdvancedContentDeduplicator()
    
    # 2. Validation and Versioning
    validation_result = validator.validate_folder(input_dir)
    new_or_modified, _ = vt.detect_changes(validation_result.valid_paths, reader=read_any)
    
    # Filter out already processed paths
    paths_to_process = [p for p in new_or_modified if p not in processed_paths]
    if not paths_to_process:
        print("No new documents to process")
        return checkpoint["results"] if checkpoint["results"] else {
            "status": "completed", 
            "message": "No new documents to process"
        }
    
    print(f"Processing {len(paths_to_process)} new documents out of {len(new_or_modified)} modified documents")
    docs_to_process = build_documents(paths_to_process)

    # 3. Domain Guardian and Deduplication
    processing_plan = guardian.enforce_processing_limits(docs_to_process)
    print(f"Processing plan decisions:")
    for decision in processing_plan.decisions:
        print(f"  {decision.path}: {decision.action} ({decision.reason or 'no reason'})")

    paths_to_process_after_guardian = {d.path for d in processing_plan.decisions if d.action != "skip"}
    docs_after_guardian = [doc for doc in docs_to_process if doc.path in paths_to_process_after_guardian]
    print(f"Documents after guardian filtering: {len(docs_after_guardian)}")

    unique_docs = dedup.detect_semantic_duplicates(docs_after_guardian)
    print(f"Documents after deduplication: {len(unique_docs)}")

    # 4. Parallel Extraction with dynamic worker count
    optimal_workers = guardian.resource_monitor.get_optimal_workers()
    # Stability override: Cap workers to prevent LLM instability on high-load systems.
    stable_workers = min(optimal_workers, 4)
    print(f"Using {stable_workers} workers (stable cap) based on current system state")

    with ThreadPoolExecutor(max_workers=stable_workers) as executor:
        future_to_doc = {executor.submit(process_single_document, doc): doc for doc in unique_docs}
        
        # Process results as they complete
        for future in as_completed(future_to_doc):
            result = future.result()
            doc_path = result["path"]

            if result["status"] == "success":
                summary["processed"] += 1
                if result.get("extracted_data"):
                    summary["successful_extractions"] = summary.get("successful_extractions", 0) + 1
            
            # Record version regardless of outcome to avoid reprocessing errors
            vt.record_file(result["path"], result.get("content", ""))
            
            # Mark as processed and save checkpoint periodically
            processed_paths.add(doc_path)
            if summary["processed"] % 5 == 0:  # Save checkpoint every 5 documents
                checkpoint_results = {
                    "summary": summary,
                }
                checkpoint_mgr.save_checkpoint(processed_paths, checkpoint_results)

    # 5. Final Report
    report = {
        "files_validated": len(validation_result.valid_paths),
        "files_changed": len(new_or_modified),
        "files_processed_after_dedup": len(unique_docs),
        "successful_extractions": summary.get("successful_extractions", 0),
    }
    
    # Clear checkpoint after successful completion
    checkpoint_mgr.clear_checkpoint()
    
    # Save the final report to a JSON file
    output_filename = "extraction_report.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4)
    print(f"\n--- SUCCESS: Report saved to {output_filename} ---\n")
    
    print("Pipeline finished. Report:", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Folder with documents")
    args = parser.parse_args()
    main(args.input) 