# Performance Monitor
"""
This module provides performance monitoring and analytics for the medical spell checker.
"""

import time
from collections import defaultdict

class PerformanceMonitor:
    def __init__(self):
        self.stats = defaultdict(lambda: defaultdict(int))
        self.response_times = defaultdict(list)

    def log_request(self, endpoint: str, operation: str):
        self.stats[endpoint][operation] += 1

    def log_cache_hit(self, endpoint: str, operation: str):
        self.stats[endpoint]['cache_hits'] += 1

    def log_cache_miss(self, endpoint: str, operation: str):
        self.stats[endpoint]['cache_misses'] += 1

    def log_response_time(self, endpoint: str, operation: str, response_time_ms: float):
        self.response_times[f"{endpoint}_{operation}"].append(response_time_ms)

    def get_stats(self):
        return self.stats

    def get_avg_response_time(self, endpoint: str, operation: str) -> float:
        times = self.response_times[f"{endpoint}_{operation}"]
        if not times:
            return 0.0
        return sum(times) / len(times)

    def get_summary(self):
        summary = {}
        for endpoint, operations in self.stats.items():
            summary[endpoint] = {}
            for op, count in operations.items():
                summary[endpoint][op] = count
            summary[endpoint]['avg_response_time'] = self.get_avg_response_time(endpoint, 'search')
        return summary

# Singleton instance
performance_monitor = PerformanceMonitor()

def get_performance_monitor():
    return performance_monitor
