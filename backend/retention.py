import os
from datetime import datetime, timedelta, timezone

from db_models import EnrollmentBuffer, TrustLog
from logging_config import log_security_event
from sqlalchemy.orm import Session

RETENTION_ENROLLMENT_DAYS = int(os.environ.get("RETENTION_ENROLLMENT_DAYS", "30"))
RETENTION_TRUST_LOGS_DAYS = int(os.environ.get("RETENTION_TRUST_LOGS_DAYS", "90"))


def enforce_data_retention_policy(db: Session) -> dict:
    """
    Automated data retention and privacy cleanup service.
    Prunes expired raw biometric enrollment buffers and granular trust logs.
    """
    now = datetime.now(timezone.utc)

    # 1. Prune raw biometric enrollment telemetry older than RETENTION_ENROLLMENT_DAYS
    enrollment_cutoff = now - timedelta(days=RETENTION_ENROLLMENT_DAYS)
    deleted_buffers = (
        db.query(EnrollmentBuffer)
        .filter(EnrollmentBuffer.created_at < enrollment_cutoff)
        .delete(synchronize_session=False)
    )

    # 2. Prune granular trust logs older than RETENTION_TRUST_LOGS_DAYS
    trust_logs_cutoff = now - timedelta(days=RETENTION_TRUST_LOGS_DAYS)
    deleted_logs = (
        db.query(TrustLog)
        .filter(TrustLog.timestamp < trust_logs_cutoff)
        .delete(synchronize_session=False)
    )

    db.commit()

    result = {
        "status": "success",
        "deleted_enrollment_buffers": deleted_buffers,
        "deleted_trust_logs": deleted_logs,
        "enrollment_retention_days": RETENTION_ENROLLMENT_DAYS,
        "trust_logs_retention_days": RETENTION_TRUST_LOGS_DAYS,
    }

    log_security_event(
        event="data_retention_cleanup",
        actor="system",
        result="SUCCESS",
        deleted_buffers=deleted_buffers,
        deleted_logs=deleted_logs,
    )

    return result
