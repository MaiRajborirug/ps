import base64
import json
import threading
import time
import traceback
from datetime import datetime

from flask import Blueprint, request
from flask_cors import cross_origin
from google.cloud import pubsub_v1

from config import PROJECT_ID, GRADE_RETRY_TOPIC_ID, MAX_GRADE_RETRIES
from src.response import success, not_found, bad_request, internal_error
from src.services.grading import grade_edspeak_assessment
from src.services.lease import try_claim, mark_done, mark_retry, mark_failed

bp = Blueprint('view', __name__)

# Lazy init — publisher is created on first use so the app can start without GCP creds locally
_publisher = None
_retry_topic_path = None


def _elapsed(start_time):
    return f"{(datetime.now() - start_time).total_seconds():.1f}s"


def _elapsed_hr_min(start_time):
    """Return '+H:MM' since start_time, e.g. '+1:05' for 1hr 5min."""
    if start_time is None:
        return "+0:00"
    td = datetime.now() - start_time
    total_secs = int(td.total_seconds())
    h, remainder = divmod(max(0, total_secs), 3600)
    m = remainder // 60
    return f"+{h}:{m:02d}"


def _get_publisher():
    global _publisher, _retry_topic_path
    if _publisher is None:
        _publisher = pubsub_v1.PublisherClient()
        _retry_topic_path = _publisher.topic_path(PROJECT_ID, GRADE_RETRY_TOPIC_ID)
    return _publisher, _retry_topic_path


def _parse(req):
    raw_decoded = req.data.decode("utf-8")
    json_data = json.loads(raw_decoded)
    message = json_data["message"]
    data = message["data"]
    return base64.b64decode(data).decode("utf-8")


def _publish_retry(assessment_instance_id, cefr, retry_count, start_time=None):
    message = json.dumps(
        {
            "assessmentInstanceId": assessment_instance_id,
            "cefr": cefr,
            "retryCount": retry_count,
            "startTime": start_time.isoformat() if start_time else None,
        }
    ).encode("utf-8")
    publisher, retry_topic_path = _get_publisher()
    future = publisher.publish(retry_topic_path, message)
    elapsed = f"(+{_elapsed(start_time)})" if start_time else ""
    print(f"#{assessment_instance_id} [RETRY] {elapsed} published retry #{retry_count}, message_id: {future.result()}")


def grade_in_background(assessment_instance_id, cefr, retry_count, start_time, result_holder):
    try:
        result = grade_edspeak_assessment(
            assessment_instance_id, 
            cefr, 
            start_time=start_time
        )
        overall_score = result["overall_score"]

        if overall_score != -1:
            print(f"#{assessment_instance_id} [BG] (+{_elapsed(start_time)}) grading completed, score: {overall_score}, attempt: {retry_count}")
            mark_done(assessment_instance_id)
            result_holder[0] = "done"
        elif retry_count < MAX_GRADE_RETRIES:
            print(f"#{assessment_instance_id} [BG-RETRY] (+{_elapsed(start_time)}) score -1, attempt: {retry_count}, retrying...")
            mark_retry(assessment_instance_id, retry_count + 1)
            _publish_retry(assessment_instance_id, cefr, retry_count + 1, start_time=start_time)
            result_holder[0] = "done"
        else:
            print(f"#{assessment_instance_id} [BG-FAILED] (+{_elapsed(start_time)}) all {retry_count + 1} attempts exhausted")
            mark_failed(assessment_instance_id)
            result_holder[0] = "done"
    except Exception as e:
        # Signal crash back to the HTTP handler so it returns 500 (NACK).
        # Pub/Sub will keep retrying; once the lease expires the next retry re-claims.
        result_holder[0] = "crashed"
        print(f"#{assessment_instance_id} [BG-PERMANENT] (+{_elapsed(start_time)}) unexpected crash: {e}")
        traceback.print_exc()


@bp.route("/v2/<assessment_instance_id>/grade", methods=["POST"])
@cross_origin()
def grade_assessment_instance(assessment_instance_id, cefr=None, retry_count=0, start_time=None):
    class UserAnswers:
        def __init__(self, answers):
            # toy class that collects voices answers
            self.user_answers = answers
    
    def get_user_answers_by_assessment_instance(assessment_instance_id):
        try:
            int(assessment_instance_id)  # accepts int and integer-like strings (e.g., "2", "-3")
        except (TypeError, ValueError):
            print(f"#{assessment_instance_id} [not int] -> need int")
            return None
        print(f"#{assessment_instance_id} [int] -> validated id")
        return UserAnswers(["sound1", "sound2", "sound3"])
    
    answers = get_user_answers_by_assessment_instance(assessment_instance_id)

    if not answers or not answers.user_answers:
        return bad_request("No answers found for assessment instance")
    
    
    # --- Distributed dedup via Datastore atomic lease ---
    claim_result, _ = try_claim(assessment_instance_id)

    if claim_result == "skip":
        print(f"#{assessment_instance_id} [SKIP] already done or failed, acking")
        return success("[ACK] already done or failed")

    if claim_result == "active":
        # Another instance holds a valid lease. NACK so Pub/Sub retries later;
        # if that instance crashes, the lease expires and a subsequent retry re-claims.
        print(f"#{assessment_instance_id} [NACK] active lease held by another instance")
        return internal_error("[NACK] active lease - retry later")

    # claim_result == "claimed" — this instance owns the lease, proceed
    if start_time is None:
        start_time = datetime.now()

    print(f"#{assessment_instance_id} [START] (+{_elapsed(start_time)}) grading request, attempt: {retry_count}")

    result_holder = ["pending"]
    try:
        # Hold response open — keeps Cloud Run instance alive for the full grading duration.
        # Lease duration (65 min) > Cloud Run max timeout (60 min), so the lease covers
        # the worst-case grading time and auto-expires on crash for self-healing recovery.
        thread = threading.Thread(
            target=grade_in_background,
            args=(assessment_instance_id, cefr, retry_count, start_time, result_holder),
            daemon=True,
        )
        thread.start()
        # print time when thread started
        thread.join()  # Block response until grading completes
    except Exception as e:
        print(f"#{assessment_instance_id} Error grading: {e}")
        traceback.print_exc()
        result_holder[0] = "crashed"

    if result_holder[0] == "crashed":
        # Return 500 so Pub/Sub keeps retrying. The lease will expire and the next
        # retry will re-claim the job — no student is permanently stuck.
        print(f"#{assessment_instance_id} [NACK-CRASH] (+{_elapsed(start_time)}) crash detected, nacking")
        return internal_error("[NACK] grading crashed - will retry")

    print(f"#{assessment_instance_id} [DONE] (+{_elapsed(start_time)}) response returning, attempt: {retry_count}")
    return success(f"[ACK] grading done for {assessment_instance_id}, attempt: {retry_count}")


@bp.route("/edspeak/grade", methods=["POST"])
@cross_origin()
def grade_edspeak_test():
    parsed = json.loads(_parse(request))
    ts = datetime.now().isoformat()
    assessment_instance_id = parsed.get("assessmentInstanceId")
    start_time_str = parsed.get("startTime")
    start_time = datetime.fromisoformat(start_time_str) if start_time_str else None
    ref_time = start_time if start_time else datetime.now()
    elapsed_str = _elapsed_hr_min(ref_time)
    print(f"            #{assessment_instance_id} [P/S] | time {elapsed_str} | {ts}")
    cefr = parsed.get("cefr")
    retry_count = parsed.get("retryCount", 0)
    return grade_assessment_instance(
        assessment_instance_id, 
        cefr=cefr, 
        retry_count=retry_count, 
        start_time=start_time,
)


@bp.route("/foo", methods=["GET"])
def test():
    print("/foo endpoint was called!")
    return success("Hi Universe!")

