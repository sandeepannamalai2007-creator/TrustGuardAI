import json
import logging
import re
import sys
from datetime import datetime, timezone

# Sensitivity regex patterns to redact from logs
SENSITIVE_KEYS = re.compile(
    r"(password|pin|admin_pin|step_up_pin|secret|jwt|token|authorization|keystrokes|raw_telemetry)",
    re.IGNORECASE,
)


class JSONStructuredFormatter(logging.Formatter):
    """Formats log records as structured JSON, sanitizing sensitive keys."""

    def sanitize_val(self, key: str, val: str | dict | list) -> str | dict | list:
        if SENSITIVE_KEYS.search(str(key)):
            return "[REDACTED]"
        if isinstance(val, dict):
            return {k: self.sanitize_val(k, v) for k, v in val.items()}
        if isinstance(val, list):
            return [self.sanitize_val(key, item) for item in val]
        return val

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Attach structured context attributes if attached to LogRecord
        for attr in ("event", "request_id", "session_id", "user_id", "actor", "action", "status_code"):
            if hasattr(record, attr):
                log_data[attr] = getattr(record, attr)

        # Sanitize any dictionary or key-value structures
        sanitized = {k: self.sanitize_val(k, v) for k, v in log_data.items()}

        if record.exc_info:
            sanitized["exception"] = self.formatException(record.exc_info)

        return json.dumps(sanitized)


def setup_structured_logging():
    """Configures structured JSON logging for the TrustGuard application."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONStructuredFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Avoid duplicate handlers
    root_logger.handlers = [handler]

    # Silence overly verbose third-party loggers
    logging.getLogger("uvicorn.access").handlers = [handler]
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


# Helper function to log structured security events
def log_security_event(event: str, level: int = logging.INFO, **kwargs):
    logger = logging.getLogger("trustguard.security")
    extra = {"event": event}
    extra.update(kwargs)
    logger.log(level, f"Security Event: {event}", extra=extra)
