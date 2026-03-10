from datetime import datetime, timedelta, timezone

from google.cloud import datastore

from config import PROJECT_ID, NAMESPACE, DATASTORE_DATABASE_ID, GRADING_STATUS_KIND, LEASE_DURATION_MINUTES

_client = None


def _get_client():
    global _client
    if _client is None:
        # get datastore client with project_id, database_id,
        # namespace, ... create on the code
        _client = datastore.Client(
            project=PROJECT_ID,
            namespace=NAMESPACE,
            database=DATASTORE_DATABASE_ID,
        )
    return _client


def _now():
    return datetime.now(tz=timezone.utc)


def _lease_expiry():
    return _now() + timedelta(minutes=LEASE_DURATION_MINUTES)


def _aware(dt):
    """Make a datetime timezone-aware (UTC) if it isn't already."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def try_claim(assessment_instance_id):
    """
    Atomically claim a grading job via a Datastore transaction.

    State machine:
        (none)   → grading                     first message
        grading  → done                         score OK
        grading  → retry                        score = -1, retries left
        grading  → failed                       score = -1, retries exhausted
        retry    → grading                      next message re-claims

    Returns:
        ('claimed', retry_count)  – this instance should proceed with grading
        ('active',  retry_count)  – another instance holds a valid lease → NACK
        ('skip',    retry_count)  – job is done/failed → ACK and ignore
    """
    client = _get_client()
    key = client.key(GRADING_STATUS_KIND, assessment_instance_id)
    now = _now()

    with client.transaction():
        entity = client.get(key)

        if entity is None:
            # First encounter — create and claim
            entity = datastore.Entity(key=key)
            entity.update({
                "status": "grading",
                "retry_count": 0,
                "lease_expires_at": _lease_expiry(),
                "started_at": now,
                "updated_at": now,
            })
            client.put(entity)
            return "claimed", 0

        status = entity.get("status")
        retry_count = entity.get("retry_count", 0)
        lease_expires_at = _aware(entity.get("lease_expires_at"))

        if status in ("done", "failed"):
            return "skip", retry_count

        if status == "grading":
            if lease_expires_at and now < lease_expires_at:
                # Active lease — another instance is working on it
                return "active", retry_count
            # Lease expired — instance likely crashed; re-claim
            entity["lease_expires_at"] = _lease_expiry()
            entity["updated_at"] = now
            client.put(entity)
            return "claimed", retry_count

        if status == "retry":
            # Application-level retry ready to be claimed
            entity.update({
                "status": "grading",
                "lease_expires_at": _lease_expiry(),
                "updated_at": now,
            })
            client.put(entity)
            return "claimed", retry_count

        # Unknown status — treat as terminal to avoid infinite loop
        return "skip", retry_count


def store_sleep_time(assessment_instance_id, sleep_time):
    _write_status(assessment_instance_id, {}, sleep_time=sleep_time)


def mark_done(assessment_instance_id):
    _write_status(assessment_instance_id, {"status": "done"})


def mark_retry(assessment_instance_id, retry_count):
    _write_status(assessment_instance_id, {"status": "retry", "retry_count": retry_count})


def mark_failed(assessment_instance_id):
    _write_status(assessment_instance_id, {"status": "failed"})


def _write_status(assessment_instance_id, updates, sleep_time=None):
    client = _get_client()
    key = client.key(GRADING_STATUS_KIND, assessment_instance_id)
    with client.transaction():
        entity = client.get(key)
        if entity:
            now = _now()
            extra = {"updated_at": now}
            if updates.get("status") in ("done", "failed"):
                started_at = _aware(entity.get("started_at"))
                if started_at:
                    extra["duration_sec"] = round((now - started_at).total_seconds(), 1)
            if sleep_time is not None:
                extra["sleep_time"] = sleep_time
            entity.update({**updates, **extra})
            client.put(entity)

