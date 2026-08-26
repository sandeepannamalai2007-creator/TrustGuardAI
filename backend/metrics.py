import threading
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class MetricsCollector:
    """
    Low-cardinality Prometheus metrics collector for production monitoring.
    Never exposes raw user IDs, session IDs, or sensitive biometric data in labels.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.request_counts = defaultdict(int)
        self.request_latency_sum = defaultdict(float)

        # Counter metrics
        self.auth_failures = 0
        self.step_up_failures = 0
        self.session_locks = 0
        self.admin_overrides = 0
        self.model_prediction_count = 0
        self.retraining_attempts = 0
        self.retraining_rejections = 0
        self.model_rollbacks = 0

        # Trust score distribution buckets
        self.trust_score_buckets = {
            "0_20": 0,
            "20_40": 0,
            "40_60": 0,
            "60_80": 0,
            "80_100": 0,
        }

    def record_request(self, method: str, path: str, status_code: int, latency: float):
        # Sanitize path to prevent high cardinality (e.g. normalize /session/123 -> /session/{id})
        clean_path = path.split("?")[0]
        if clean_path.startswith("/session/") and len(clean_path.split("/")) > 2:
            parts = clean_path.split("/")
            if parts[2].isalnum() or len(parts[2]) > 8:
                parts[2] = "{session_id}"
            clean_path = "/".join(parts)

        key = f"{method} {clean_path} {status_code}"
        with self._lock:
            self.request_counts[key] += 1
            self.request_latency_sum[key] += latency

    def record_auth_failure(self):
        with self._lock:
            self.auth_failures += 1

    def record_step_up_failure(self):
        with self._lock:
            self.step_up_failures += 1

    def record_session_lock(self):
        with self._lock:
            self.session_locks += 1

    def record_admin_override(self):
        with self._lock:
            self.admin_overrides += 1

    def record_trust_score(self, score: float):
        """Backward compatible helper for recording trust score and updating distribution."""
        self.record_model_prediction(score)

    def record_model_prediction(self, trust_score: float):
        with self._lock:
            self.model_prediction_count += 1
            if trust_score < 20:
                self.trust_score_buckets["0_20"] += 1
            elif trust_score < 40:
                self.trust_score_buckets["20_40"] += 1
            elif trust_score < 60:
                self.trust_score_buckets["40_60"] += 1
            elif trust_score < 80:
                self.trust_score_buckets["60_80"] += 1
            else:
                self.trust_score_buckets["80_100"] += 1

    def record_retraining_attempt(self, success: bool = True):
        with self._lock:
            self.retraining_attempts += 1
            if not success:
                self.retraining_rejections += 1

    def record_model_rollback(self):
        with self._lock:
            self.model_rollbacks += 1

    def generate_prometheus_output(self) -> str:
        lines = [
            "# HELP trustguard_http_requests_total Total HTTP requests.",
            "# TYPE trustguard_http_requests_total counter",
        ]
        with self._lock:
            for key, count in self.request_counts.items():
                parts = key.split()
                method, path, status = parts[0], parts[1], parts[2]
                lines.append(
                    f'trustguard_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
                )

            lines.extend(
                [
                    "# HELP trustguard_http_request_duration_seconds_sum Total request latency.",
                    "# TYPE trustguard_http_request_duration_seconds_sum counter",
                ]
            )
            for key, total_latency in self.request_latency_sum.items():
                parts = key.split()
                method, path, status = parts[0], parts[1], parts[2]
                lines.append(
                    f'trustguard_http_request_duration_seconds_sum{{method="{method}",path="{path}",status="{status}"}} {total_latency:.6f}'
                )

            lines.extend(
                [
                    "# HELP trustguard_auth_failures_total Total authentication failures.",
                    "# TYPE trustguard_auth_failures_total counter",
                    f"trustguard_auth_failures_total {self.auth_failures}",
                    "# HELP trustguard_step_up_failures_total Total step-up verification failures.",
                    "# TYPE trustguard_step_up_failures_total counter",
                    f"trustguard_step_up_failures_total {self.step_up_failures}",
                    "# HELP trustguard_session_locks_total Total session forced locks.",
                    "# TYPE trustguard_session_locks_total counter",
                    f"trustguard_session_locks_total {self.session_locks}",
                    "# HELP trustguard_admin_overrides_total Total admin override operations.",
                    "# TYPE trustguard_admin_overrides_total counter",
                    f"trustguard_admin_overrides_total {self.admin_overrides}",
                    "# HELP trustguard_model_predictions_total Total ML model trust score predictions.",
                    "# TYPE trustguard_model_predictions_total counter",
                    f"trustguard_model_predictions_total {self.model_prediction_count}",
                    "# HELP trustguard_model_retrain_attempts_total Total model retraining attempts.",
                    "# TYPE trustguard_model_retrain_attempts_total counter",
                    f"trustguard_model_retrain_attempts_total {self.retraining_attempts}",
                    "# HELP trustguard_model_retrain_rejections_total Total model retraining performance rejections.",
                    "# TYPE trustguard_model_retrain_rejections_total counter",
                    f"trustguard_model_retrain_rejections_total {self.retraining_rejections}",
                    "# HELP trustguard_model_rollbacks_total Total model rollbacks executed.",
                    "# TYPE trustguard_model_rollbacks_total counter",
                    f"trustguard_model_rollbacks_total {self.model_rollbacks}",
                ]
            )

            # Trust score distribution buckets
            lines.extend(
                [
                    "# HELP trustguard_trust_score_distribution_bucket Histogram count of predicted trust scores by range.",
                    "# TYPE trustguard_trust_score_distribution_bucket counter",
                ]
            )
            for bucket, count in self.trust_score_buckets.items():
                lines.append(
                    f'trustguard_trust_score_distribution_bucket{{range="{bucket}"}} {count}'
                )

        return "\n".join(lines) + "\n"


metrics_collector = MetricsCollector()


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        import time

        start_time = time.time()
        response = await call_next(request)
        latency = time.time() - start_time
        metrics_collector.record_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency=latency,
        )
        return response
