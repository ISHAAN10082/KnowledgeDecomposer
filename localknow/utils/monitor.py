"""
System monitoring utilities optimized for Apple Silicon.
"""
import os
import time
import platform
import threading
from typing import Dict, List, Optional, Callable
import psutil

class AppleSiliconMonitor:
    """
    Resource monitor optimized for Apple Silicon's unified memory architecture.
    Provides real-time monitoring of CPU, GPU, and memory usage.
    """
    
    def __init__(self, interval: float = 2.0):
        """
        Initialize the monitor.
        
        Args:
            interval: Sampling interval in seconds
        """
        self.interval = interval
        self.is_apple_silicon = platform.processor() == 'arm'
        self.total_memory = psutil.virtual_memory().total
        self.monitoring = False
        self._thread = None
        self.history: List[Dict] = []
        self.max_history = 100
        self.callbacks: List[Callable] = []
        
    def start(self):
        """Start background monitoring."""
        if self._thread and self._thread.is_alive():
            return
            
        self.monitoring = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        """Stop background monitoring."""
        self.monitoring = False
        if self._thread:
            self._thread.join(timeout=self.interval*2)
            
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.monitoring:
            stats = self.get_current_stats()
            self.history.append(stats)
            
            # Keep history within limits
            while len(self.history) > self.max_history:
                self.history.pop(0)
                
            # Call any registered callbacks
            for callback in self.callbacks:
                try:
                    callback(stats)
                except Exception as e:
                    print(f"Error in monitoring callback: {e}")
                    
            time.sleep(self.interval)
    
    def get_current_stats(self) -> Dict:
        """Get current system statistics."""
        stats = {
            'timestamp': time.time(),
            'memory': {},
            'cpu': {},
            'disk': {},
        }
        
        # Memory stats
        mem = psutil.virtual_memory()
        stats['memory'] = {
            'total_gb': mem.total / (1024**3),
            'used_gb': mem.used / (1024**3),
            'available_gb': mem.available / (1024**3),
            'percent': mem.percent,
            'swap_used_gb': psutil.swap_memory().used / (1024**3) if hasattr(psutil, 'swap_memory') else 0
        }
        
        # CPU stats
        cpu_percent = psutil.cpu_percent(interval=0.1, percpu=True)
        stats['cpu'] = {
            'percent_per_core': cpu_percent,
            'average_percent': sum(cpu_percent) / len(cpu_percent),
            'core_count': len(cpu_percent),
            'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
        }
        
        # Disk stats
        disk = psutil.disk_io_counters()
        stats['disk'] = {
            'read_mb': disk.read_bytes / (1024**2),
            'write_mb': disk.write_bytes / (1024**2),
            'read_count': disk.read_count,
            'write_count': disk.write_count
        }
        
        # Process specific stats
        current_process = psutil.Process(os.getpid())
        stats['process'] = {
            'memory_gb': current_process.memory_info().rss / (1024**3),
            'cpu_percent': current_process.cpu_percent(interval=0.1),
            'threads': current_process.num_threads()
        }
        
        return stats
    
    def register_callback(self, callback: Callable[[Dict], None]):
        """Register a callback to be called with each stats update."""
        self.callbacks.append(callback)
        
    def unregister_callback(self, callback: Callable):
        """Unregister a previously registered callback."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def get_memory_pressure(self) -> float:
        """Get memory pressure as a value between 0 and 1."""
        if not self.history:
            stats = self.get_current_stats()
            return stats['memory']['percent'] / 100.0
            
        # Use recent history to determine memory pressure
        recent = self.history[-min(5, len(self.history)):]
        avg_memory_percent = sum(s['memory']['percent'] for s in recent) / len(recent)
        return avg_memory_percent / 100.0
    
    def get_optimal_workers(self) -> int:
        """
        Calculate optimal worker count based on system resources.
        
        For Apple Silicon, we need to be more conservative with workers due to
        the unified memory architecture.
        """
        stats = self.get_current_stats()
        
        # Base calculation - physical cores minus 1 for system
        if self.is_apple_silicon:
            # On Apple Silicon, start with physical cores minus 2
            base_count = max(2, stats['cpu']['core_count'] - 2)
        else:
            # On other systems, use physical cores minus 1
            base_count = max(2, stats['cpu']['core_count'] - 1)
            
        # Adjust for memory pressure
        memory_pressure = self.get_memory_pressure()
        if memory_pressure > 0.8:
            # High memory pressure - reduce workers
            base_count = max(2, base_count // 2)
        elif memory_pressure < 0.3 and stats['memory']['available_gb'] > 8:
            # Low memory pressure with plenty available - can add workers
            base_count = min(stats['cpu']['core_count'], base_count + 2)
            
        return base_count
        
    def print_summary(self):
        """Print a human-readable summary of current system state."""
        stats = self.get_current_stats()
        
        print("\n=== System Resource Summary ===")
        print(f"Memory: {stats['memory']['percent']:.1f}% used "
              f"({stats['memory']['used_gb']:.1f}GB / {stats['memory']['total_gb']:.1f}GB)")
        print(f"CPU: {stats['cpu']['average_percent']:.1f}% avg across {stats['cpu']['core_count']} cores")
        print(f"Current Process: {stats['process']['memory_gb']*1024:.1f}MB RAM, "
              f"{stats['process']['cpu_percent']:.1f}% CPU")
        print(f"Recommended Workers: {self.get_optimal_workers()}")
        print("==============================\n")


# Singleton instance for app-wide use
monitor = AppleSiliconMonitor()

if __name__ == "__main__":
    # Example usage
    monitor.start()
    try:
        for _ in range(5):
            monitor.print_summary()
            time.sleep(2)
    finally:
        monitor.stop() 