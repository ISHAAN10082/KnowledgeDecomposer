from fastapi import FastAPI, BackgroundTasks, UploadFile, File
from pydantic import BaseModel
from typing import Dict, Any
import json
import shutil
from pathlib import Path

from intellidoc.pipeline.orchestrator import main as run_pipeline, process_document_path
from intellidoc.utils.monitor import monitor
from intellidoc.config import settings

# Start the system monitor
monitor.start()

app = FastAPI(title="IntelliDoc Extractor API")

# In-memory store for job results
results: Dict[str, Any] = {}

class IngestRequest(BaseModel):
    input_dir: str

TEMP_DIR = Path("temp_uploads")
TEMP_DIR.mkdir(exist_ok=True)

@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    """Extracts structured data from a single uploaded document."""
    temp_path = TEMP_DIR / file.filename
    try:
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Run single document processing
        result = process_document_path(str(temp_path))
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        # Clean up the temporary file
        if temp_path.exists():
            temp_path.unlink()

@app.get("/health")
async def health():
    stats = monitor.get_current_stats()
    return {
        "status": "ok",
        "system": {
            "memory_used_percent": round(stats["memory"]["percent"], 1),
            "cpu_percent": round(stats["cpu"]["average_percent"], 1),
            "available_memory_gb": round(stats["memory"]["available_gb"], 1),
            "optimal_workers": monitor.get_optimal_workers()
        }
    }

@app.get("/stats")
async def system_stats():
    """Get detailed system statistics."""
    stats = monitor.get_current_stats()
    return stats

def run_pipeline_background(job_id: str, input_dir: str):
    """Wrapper to run pipeline and store results."""
    try:
        # Print system state before starting
        monitor.print_summary()
        
        report = run_pipeline(input_dir)
        results[job_id] = report
        
        # Print system state after completion
        monitor.print_summary()
    except Exception as e:
        results[job_id] = {"status": "error", "error": str(e)}

@app.post("/ingest")
async def ingest(req: IngestRequest, background_tasks: BackgroundTasks):
    job_id = "last_run" # For simplicity, only store the last run
    results[job_id] = {
        "status": "running", 
        "dir": req.input_dir,
        "system_state": monitor.get_current_stats()
    }
    background_tasks.add_task(run_pipeline_background, job_id, req.input_dir)
    return {"status": "ingestion_started", "job_id": job_id}

@app.get("/results/{job_id}")
async def get_results(job_id: str):
    return results.get(job_id, {"status": "not_found"})

@app.on_event("shutdown")
def shutdown_event():
    """Clean up resources when shutting down."""
    monitor.stop() 