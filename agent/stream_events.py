"""
stream_events.py - Simple event streaming with timing and LLM stats
"""
from typing import Dict, Any
from queue import Queue, Empty
from contextlib import contextmanager
import time
import logging
import json
from llm_integration import chat_completion

logger = logging.getLogger(__name__)

class StreamProcessor:
    def __init__(self):
        self.stats_queue = Queue()
        self.timings: Dict[str, float] = {}
        self._stage_times: Dict[str, float] = {}

    @contextmanager
    def stage(self, name: str):
        """Time a processing stage using a context manager"""
        try:
            self._stage_times[name] = time.time()
            yield
        finally:
            if name in self._stage_times:
                self.timings[name] = (time.time() - self._stage_times[name]) * 1000

    def chat(self, messages: list[dict], model_name: str, **kwargs) -> str:
        """Execute chat completion with automatic stats collection"""
        return chat_completion(
            messages=messages,
            model_name=model_name,
            stats_queue=self.stats_queue,
            **kwargs
        )

    def event(self, stage: str, data: Dict[str, Any]) -> str:
        """Create a stream event with timing and any available LLM stats"""
        event_data = {"stage": stage, **data}
        
        if stage in self.timings:
            event_data["timing"] = self.timings[stage]

        # Collect stats without blocking
        stats = {"total_tokens": 0}
        while True:
            try:
                usage = self.stats_queue.get_nowait()
                for key, value in usage.items():
                    if isinstance(value, (int, float)):
                        stats[key] = stats.get(key, 0) + value
            except Empty:
                break
        
        if stats["total_tokens"] > 0:
            event_data["llm_stats"] = stats

        if stage in ("complete", "error"):
            event_data["timings"] = self.timings

        output = f"data: {json.dumps(event_data)}\n\n"
        logger.info(f"streaming: {output}")
        return output
