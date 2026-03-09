import os
from dotenv import load_dotenv

load_dotenv()

#######################################################################
# Datastore config
#######################################################################
NAMESPACE = os.environ.get("NAMESPACE")
ACCESS_CODE_KIND = "access-code"
TESTER_KIND = "tester"
TESTINSTANCE_KIND = "test-instance"
SPEAKING_QUESTION_KIND = "speaking-question"
SPEAKING_TEST_KIND = "speaking-test"
PRETEST_QUESTION_GROUP_KIND = "pretest-question-group"
SCHOOL_KIND = "school"
PROJECT_ID = "edsy-ps-proj"
PRD_NS = "assess-prd"

if NAMESPACE == "assess-prd":
    FIRST_PRETEST_QUESTION_GROUP = "8003d1c94bf2454c873c472f6770d8c7"  # prd
    ENV = "prd"
    BUCKET_NAME = "prod-edsy-assess"
else:
    FIRST_PRETEST_QUESTION_GROUP = "c97cfb47bec54a3fa826dd5a1ec59e33"  # dev
    ENV = "dev"
    BUCKET_NAME = "dev-edsy-assess"

PRETEST_THRESHOLD = 0.6
GRADE_TOPIC_ID = os.environ.get("GRADE_TOPIC_ID", "edspeak-grade")  # Pub/Sub topic id
GRADE_RETRY_TOPIC_ID = os.environ.get("GRADE_RETRY_TOPIC_ID", "edspeak-grade-retry") # Pub/Sub topic id for application retries
MAX_GRADE_RETRIES = 1
DATASTORE_DATABASE_ID = "ps-database" # GCP Datastore database id
GRADING_STATUS_KIND = "grading-status"
# Cloud Run max request timeout is 3600 s (60 min); +5 min buffer for slow LLM tail
LEASE_DURATION_MINUTES = 65

# Version1 kinds
CODE_KIND = "school-code"
STUDENT_KIND = "student"

#######################################################################
# Cloud storage config
#######################################################################
