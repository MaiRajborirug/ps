import random
import time
from datetime import datetime


def grade_edspeak_assessment(assessment_instance_id, cefr=None, start_time=None):
    """
    Simplified grading function that simulates processing time.
    Returns overall_score (-1 or positive float 0-100) and empty update_result.
    """
    sleep_time = 60
    # if CEFR is positive integer, convert it into sleep time (seconds)
    if cefr and str(cefr).isdigit() and int(cefr) > 0: # isdigit work for both int and string
        sleep_time = int(cefr)

    if start_time is None:
        start_time = datetime.now()

    def _e():
        return f"+{(datetime.now() - start_time).total_seconds():.1f}s"

    print(f"#{assessment_instance_id} [GRADING] ({_e()}) processing (cefr={cefr}), sleeping {sleep_time:.1f}s...")
    time.sleep(sleep_time)

    # if assessment_instance_id is odd return -1
    if int(assessment_instance_id) % 2 == 1:
        print(f"#{assessment_instance_id} [GRADING] ({_e()}) score=-1 (odd id)")
        return {"overall_score": -1, "update_result": {}}

    overall_score = round(random.uniform(20, 95), 2)
    print(f"#{assessment_instance_id} [GRADING] ({_e()}) score={overall_score}")
    return {"overall_score": overall_score, "update_result": {}}
