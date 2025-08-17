import time
import functools
from typing import Callable, Any

# Simple in-memory state for the circuit breaker
circuit_breaker_state = {
    "is_open": False,
    "failure_count": 0,
    "last_failure_time": 0
}

FAILURE_THRESHOLD = 3
COOLDOWN_PERIOD = 60  # seconds

def circuit_breaker(func: Callable) -> Callable:
    """A simple circuit breaker decorator to wrap external API calls."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        global circuit_breaker_state

        state = circuit_breaker_state
        is_open = state["is_open"]
        last_failure_time = state["last_failure_time"]

        if is_open and (time.time() - last_failure_time) > COOLDOWN_PERIOD:
            # Attempt to reset the circuit (half-open state)
            state = {"is_open": False, "failure_count": 0, "last_failure_time": 0}
            circuit_breaker_state = state
        
        if state["is_open"]:
            raise ConnectionError("Circuit breaker is open. Service is unavailable.")

        try:
            result = func(*args, **kwargs)
            # Reset on success
            state["failure_count"] = 0
            return result
        except Exception as e:
            state["failure_count"] += 1
            state["last_failure_time"] = time.time()
            if state["failure_count"] >= FAILURE_THRESHOLD:
                state["is_open"] = True
                print(f"Circuit breaker opened due to {state['failure_count']} failures.")
            raise e

    return wrapper 