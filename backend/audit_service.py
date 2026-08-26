import hashlib
from datetime import datetime, timezone

from db_models import AuditLog
from logging_config import log_security_event
from sqlalchemy.orm import Session

GENESIS_HASH = "0" * 64


def calculate_entry_hash(
    previous_hash: str,
    timestamp_iso: str,
    actor: str,
    action: str,
    target: str,
    result: str,
    details: str,
    ip_address: str,
) -> str:
    """Calculates SHA-256 hash for audit record chaining."""
    payload = f"{previous_hash}|{timestamp_iso}|{actor}|{action}|{target}|{result}|{details}|{ip_address}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_audit_event(
    db: Session,
    actor: str,
    action: str,
    target: str,
    result: str,
    details: str = "",
    ip_address: str = "127.0.0.1",
) -> AuditLog:
    """
    Creates a cryptographically chained audit log entry.
    Each entry seals the previous record's hash, forming an immutable hash chain.
    """
    latest = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    previous_hash = latest.event_hash if latest else GENESIS_HASH

    now = datetime.now(timezone.utc)
    timestamp_iso = now.isoformat()

    event_hash = calculate_entry_hash(
        previous_hash=previous_hash,
        timestamp_iso=timestamp_iso,
        actor=actor,
        action=action,
        target=target,
        result=result,
        details=details,
        ip_address=ip_address,
    )

    audit_record = AuditLog(
        timestamp=now,
        actor=actor,
        action=action,
        target=target,
        result=result,
        details=details,
        ip_address=ip_address,
        previous_hash=previous_hash,
        event_hash=event_hash,
    )
    db.add(audit_record)
    db.commit()
    db.refresh(audit_record)

    # Log structured security event for SIEM/logging collectors
    log_security_event(
        event=action,
        actor=actor,
        target=target,
        result=result,
        ip_address=ip_address,
        audit_id=audit_record.id,
    )

    return audit_record


def verify_audit_log_chain(db: Session) -> dict:
    """
    Verifies the integrity of the audit log chain from start to end.
    Detects record deletion, modification, or reordering.
    """
    records = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
    if not records:
        return {"valid": True, "total_records": 0, "status": "EMPTY_CHAIN"}

    expected_previous_hash = GENESIS_HASH

    for record in records:
        if record.previous_hash != expected_previous_hash:
            return {
                "valid": False,
                "status": "TAMPERING_DETECTED",
                "record_id": record.id,
                "reason": f"Mismatched previous_hash at record {record.id}. Expected {expected_previous_hash}, got {record.previous_hash}",
            }

        timestamp_iso = record.timestamp.replace(tzinfo=timezone.utc).isoformat() if record.timestamp.tzinfo is None else record.timestamp.isoformat()
        recomputed_hash = calculate_entry_hash(
            previous_hash=record.previous_hash,
            timestamp_iso=timestamp_iso,
            actor=record.actor,
            action=record.action,
            target=record.target,
            result=record.result,
            details=record.details or "",
            ip_address=record.ip_address or "",
        )

        if record.event_hash != recomputed_hash:
            return {
                "valid": False,
                "status": "HASH_MISMATCH",
                "record_id": record.id,
                "reason": f"Recalculated hash mismatch at record {record.id}.",
            }

        expected_previous_hash = record.event_hash

    return {"valid": True, "total_records": len(records), "status": "VERIFIED_INTACT"}
