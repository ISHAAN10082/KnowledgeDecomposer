import argparse
import os
import uuid
import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import itertools

from localknow.config import settings
from localknow.core.validators import ContentValidator
from localknow.core.domain_guardian import ResourceGuardian
from localknow.core.quality import ValidationEngine
from localknow.ingestion.parsers import read_any
from localknow.ingestion.chunker import TextChunker
from localknow.persist.versioning import VersionTracker
from localknow.types import Document, Concept
from localknow.dedup.deduplicator import AdvancedContentDeduplicator
from localknow.extract.concepts import RobustConceptExtractor
from localknow.extract.principles import FirstPrinciplesExtractor
from localknow.extract.controversy import ControversyDetector
from localknow.graph.builder import HierarchicalKnowledgeBuilder


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


def process_single_document(doc: Document) -> Dict[str, Any]:
    """Orchestrates the chunking, extraction, and analysis for a single document."""
    try:
        # Initialize services used per-document
        concept_extractor = RobustConceptExtractor()
        principle_extractor = FirstPrinciplesExtractor()
        controversy_detector = ControversyDetector()
        quality_engine = ValidationEngine()
        chunker = TextChunker()

        # Chunk the document content
        chunks = chunker.chunk(doc.content)
        
        # Process each chunk to extract information
        chunk_results = []
        for chunk in chunks:
            concepts = concept_extractor.extract_with_validation(chunk)
            if not concepts:
                continue
            
            principles = principle_extractor.extract_foundational_truths(concepts, chunk)
            controversies = controversy_detector.identify_debates(concepts, chunk)
            chunk_results.append({
                "concepts": concepts,
                "principles": principles,
                "controversies": controversies
            })

        if not chunk_results:
            return {"status": "skipped", "reason": "no concepts extracted from any chunk", "doc_id": doc.document_id, "path": doc.path, "content": doc.content}

        # Aggregate results from all chunks
        all_concepts = list(itertools.chain.from_iterable(r['concepts'] for r in chunk_results))
        all_principles = list(itertools.chain.from_iterable(r['principles'] for r in chunk_results))
        all_controversies = list(itertools.chain.from_iterable(r['controversies'] for r in chunk_results))
        
        # Deduplicate aggregated results by name/topic
        unique_concepts = {c.name.lower(): c for c in all_concepts}.values()
        unique_principles = {p.name.lower(): p for p in all_principles}.values()
        unique_controversies = {c.topic.lower(): c for c in all_controversies}.values()

        quality_report = quality_engine.calculate_quality(list(unique_concepts))

        return {
            "status": "success",
            "doc_id": doc.document_id,
            "path": doc.path,
            "content": doc.content, # Return original content for versioning
            "concepts": list(unique_concepts),
            "principles": list(unique_principles),
            "controversies": list(unique_controversies),
            "quality": quality_report.avg_concept_confidence,
        }
    except Exception as e:
        print(f"Error processing {doc.path}: {e}")
        return {"status": "error", "reason": str(e), "doc_id": doc.document_id, "path": doc.path, "content": ""}


class CheckpointManager:
    """Manages checkpoints for resumable processing."""
    
    def __init__(self, input_dir: str):
        self.checkpoint_dir = Path(".localknow/checkpoints")
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
    summary = checkpoint["results"].get("summary", {"processed": 0, "concepts": 0, "principles": 0, "controversies": 0, "avg_quality": []})
    
    # 1. Initialization
    validator = ContentValidator()
    guardian = ResourceGuardian()
    vt = VersionTracker(settings.sqlite_db_path)
    dedup = AdvancedContentDeduplicator()
    builder = HierarchicalKnowledgeBuilder()
    
    # Restore graph state if available
    if "graph_json" in checkpoint["results"]:
        try:
            import networkx as nx
            graph_data = json.loads(checkpoint["results"]["graph_json"])
            builder.G = nx.node_link_graph(graph_data)
            print(f"Restored knowledge graph with {len(builder.G.nodes)} nodes")
        except Exception as e:
            print(f"Could not restore graph: {e}")

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

    # 4. Parallel Extraction and Graph Building with dynamic worker count
    optimal_workers = min(2, guardian.resource_monitor.get_optimal_workers())  # Force low worker count
    print(f"Using {optimal_workers} workers based on current system state (limited for safety)")

    # Add memory check before processing
    import psutil
    mem = psutil.virtual_memory()
    if mem.percent > 75:
        print(f"High memory usage ({mem.percent:.1f}%), reducing to single worker")
        optimal_workers = 1
    
    with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
        future_to_doc = {executor.submit(process_single_document, doc): doc for doc in unique_docs}
        
        # Process results as they complete
        for future in as_completed(future_to_doc):
            result = future.result()
            doc_path = result["path"]

            if result["status"] == "success":
                builder.add_concepts(result["concepts"], result["doc_id"])
                builder.add_principles(result["principles"], result["doc_id"])
                builder.add_controversies(result["controversies"], result["doc_id"])
                builder.map_dependencies(result["concepts"], result["principles"])

                summary["processed"] += 1
                summary["concepts"] += len(result["concepts"])
                summary["principles"] += len(result["principles"])
                summary["controversies"] += len(result["controversies"])
                summary["avg_quality"].append(result["quality"])
            
            # Record version regardless of outcome to avoid reprocessing errors
            vt.record_file(result["path"], result["content"])
            
            # Mark as processed and save checkpoint periodically
            processed_paths.add(doc_path)
            if summary["processed"] % 5 == 0:  # Save checkpoint every 5 documents
                checkpoint_results = {
                    "summary": summary,
                    "graph_json": builder.to_json()
                }
                checkpoint_mgr.save_checkpoint(processed_paths, checkpoint_results)

    final_quality = sum(summary["avg_quality"]) / len(summary["avg_quality"]) if summary["avg_quality"] else 0
    
    # 5. Final Report
    report = {
        "files_validated": len(validation_result.valid_paths),
        "files_changed": len(new_or_modified),
        "files_processed_after_dedup": len(unique_docs),
        "concepts_extracted": summary["concepts"],
        "principles_extracted": summary["principles"],
        "controversies_found": summary["controversies"],
        "average_quality_score": round(final_quality, 3),
        "graph_json": builder.to_json(),
    }
    
    # Clear checkpoint after successful completion
    checkpoint_mgr.clear_checkpoint()
    
    print("Pipeline finished. Report:", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Folder with documents")
    args = parser.parse_args()
    main(args.input) 