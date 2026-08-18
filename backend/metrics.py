import threading
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class MetricsCollector:
    def __init__(self):
        self._lock = threading.Lock()
        self.request_counts = defaultdict(int)
        self.request_latency_sum = defaultdict(float)
        self.trust_scores = []

    def record_request(self, method: str, path: str, status_code: int, latency: float):
        key = f'{method} {path} {status_code}'
        with self._lock:
            self.request_counts[key] += 1
            self.request_latency_sum[key] += latency

    def record_trust_score(self, score: float):
        with self._lock:
            self.trust_scores.append(score)
            if len(self.trust_scores) > 1000:
                self.trust_scores.pop(0)

    def generate_prometheus_output(self) -> str:
        lines = [
            "# HELP trustguard_http_requests_total Total number of HTTP requests.",
            "# TYPE trustguard_http_requests_total counter"
        ]
        with self._lock:
            for key, count in self.request_counts.items():
                parts = key.split()
                method, path, status = parts[0], parts[1], parts[2]
                lines.append(f'trustguard_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}')

            lines.extend([
                "# HELP trustguard_http_request_duration_seconds_sum Total latency in seconds for HTTP requests.",
                "# TYPE trustguard_http_request_duration_seconds_sum counter"
            ])
            for key, total_latency in self.request_latency_sum.items():
                parts = key.split()
                method, path, status = parts[0], parts[1], parts[2]
                lines.append(f'trustguard_http_request_duration_seconds_sum{{method="{method}",path="{path}",status="{status}"}} {total_latency:.6f}')

            if self.trust_scores:
                avg_score = sum(self.trust_scores) / len(self.trust_scores)
                lines.extend([
                    "# HELP trustguard_biometric_trust_score_average Moving average of biometric trust scores.",
                    "# TYPE trustguard_biometric_trust_score_average gauge",
                    f'trustguard_biometric_trust_score_average {avg_score:.2f}'
                ])
        return "\n".join(lines) + "\n"

metrics_collector = MetricsCollector()

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        latency = time.time() - start_time
        metrics_collector.record_request(request.method, request.url.path, response.status_code, latency)
        return response
