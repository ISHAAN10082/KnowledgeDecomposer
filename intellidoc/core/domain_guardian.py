import os
import psutil
import time
import platform
from typing import List, Dict, Any, Tuple

from intellidoc.config import settings
from intellidoc.types import Document, ProcessingPlan
from intellidoc.models.ollama_client import OllamaClient
from intellidoc.models.prompts import DOMAIN_CLASSIFICATION_PROMPT

# Domain categories based on expected LLM success rates
HIGH_SUCCESS_DOMAINS = {"technical", "computer_science", "mathematics", "physics", "engineering"}
MEDIUM_SUCCESS_DOMAINS = {"biology", "chemistry", "economics", "history", "finance"}
LOW_SUCCESS_DOMAINS = {"philosophy", "literature", "art"}

class ResourceMonitor:
    """Enhanced system monitor optimized for Apple Silicon."""
    
    def __init__(self):
        self.is_apple_silicon = platform.processor() == 'arm'
        self.total_memory = psutil.virtual_memory().total
        self.history = []  # Track resource usage over time
        
    def get_detailed_stats(self) -> Dict[str, float]:
        """Get detailed system stats including per-core CPU usage."""
        stats = {}
        
        # Memory stats
        mem = psutil.virtual_memory()
        stats['memory_used_percent'] = mem.percent / 100.0
        stats['memory_available_gb'] = mem.available / (1024 ** 3)
        
        # CPU stats
        cpu_percent = psutil.cpu_percent(interval=0.1, percpu=True)
        stats['cpu_average'] = sum(cpu_percent) / len(cpu_percent) / 100.0
        stats['cpu_max_core'] = max(cpu_percent) / 100.0
        
        # Disk I/O
        disk_io = psutil.disk_io_counters()
        stats['disk_busy'] = (disk_io.read_bytes + disk_io.write_bytes) > 1000000  # Simple heuristic
        
        # Track history for trend analysis
        self.history.append((time.time(), stats['memory_used_percent'], stats['cpu_average']))
        if len(self.history) > 10:  # Keep only recent history
            self.history.pop(0)
            
        return stats
    
    def get_system_load(self) -> float:
        """Returns a normalized system load (0.0 to 1.0)."""
        stats = self.get_detailed_stats()
        # Weighted average favoring memory on Apple Silicon (unified memory is critical)
        if self.is_apple_silicon:
            return 0.7 * stats['memory_used_percent'] + 0.3 * stats['cpu_average']
        else:
            return max(stats['memory_used_percent'], stats['cpu_average'])
    
    def get_optimal_workers(self) -> int:
        """Determine optimal worker count based on current system state."""
        stats = self.get_detailed_stats()
        
        # Base calculation on available resources
        base_count = settings.pipeline_workers
        
        # Adjust for high memory pressure
        if stats['memory_used_percent'] > 0.8:
            base_count = max(2, base_count // 2)
        elif stats['memory_available_gb'] > 16:  # Plenty of memory available
            base_count = min(12, base_count + 2)
            
        # Adjust for CPU load trends
        if len(self.history) > 5:
            # Calculate CPU trend
            recent_cpu = [cpu for _, _, cpu in self.history[-5:]]
            if sum(recent_cpu) / len(recent_cpu) > 0.85:  # High sustained CPU
                base_count = max(2, base_count - 1)
                
        return base_count

class DomainClassifier:
    """Classifies documents into predefined domains."""
    def __init__(self):
        self.model = OllamaClient(settings.models.validation_model)
        self.domains = HIGH_SUCCESS_DOMAINS | MEDIUM_SUCCESS_DOMAINS | LOW_SUCCESS_DOMAINS
        self.cache = {}  # Cache classifications to avoid redundant processing

    def classify(self, doc: Document) -> str:
        """Classifies document content into a domain."""
        # Use document ID for caching
        if doc.document_id in self.cache:
            return self.cache[doc.document_id]
            
        sample = doc.content[:1500]
        prompt = DOMAIN_CLASSIFICATION_PROMPT.format(
            domains=", ".join(self.domains),
            text_sample=sample
        )
        domain = self.model.generate(prompt).strip().lower().replace("_", " ")
        result = domain if domain in self.domains else "unknown"
        
        # Cache the result
        self.cache[doc.document_id] = result
        return result

class ResourceGuardian:
    """Enforces processing boundaries based on domain and system resources."""
    def __init__(self):
        self.domain_classifier = DomainClassifier()
        self.resource_monitor = ResourceMonitor()

    def enforce_processing_limits(self, documents: List[Document]) -> ProcessingPlan:
        """Creates a processing plan based on document domain and system load."""
        plan = ProcessingPlan(decisions=[])
        
        # Get detailed system stats
        stats = self.resource_monitor.get_detailed_stats()
        print(f"System state: Memory: {stats['memory_used_percent']*100:.1f}%, " 
              f"CPU: {stats['cpu_average']*100:.1f}%, "
              f"Available memory: {stats['memory_available_gb']:.1f}GB")
        
        for doc in documents:
            if stats['memory_used_percent'] > 0.9:
                plan.add_skip_processing(doc.path, reason="Critical memory pressure")
                continue

            domain = self.domain_classifier.classify(doc)

            if domain in HIGH_SUCCESS_DOMAINS:
                plan.add_full_processing(doc.path)
            elif domain in MEDIUM_SUCCESS_DOMAINS:
                if stats['memory_used_percent'] > 0.75:
                    plan.add_limited_processing(doc.path)
                else:
                    plan.add_full_processing(doc.path)
            else: # Defaults to full processing for LOW_SUCCESS_DOMAINS or "unknown"
                plan.add_full_processing(doc.path)
        return plan 