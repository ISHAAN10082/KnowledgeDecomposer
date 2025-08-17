from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any
import json

from localknow.pipeline.orchestrator import main as run_pipeline
from localknow.utils.monitor import monitor
from localknow.config import settings

# Start the system monitor
monitor.start()

app = FastAPI(title="LocalKnow API")

# In-memory store for job results
results: Dict[str, Any] = {}

class IngestRequest(BaseModel):
    input_dir: str

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