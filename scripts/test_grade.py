"""
Send a test grading POST request.

Usage:
  python scripts/test_grade.py <ID> <CEFR> [URL]

Examples:
  python scripts/test_grade.py 10 B1
  python scripts/test_grade.py 5 A2 http://localhost:8877
  python scripts/test_grade.py 5 A2 https://your-ngrok-url
"""
import base64
import json
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError

DEFAULT_URL = "http://localhost:8877"

if len(sys.argv) < 3:
    print("Usage: python scripts/test_grade.py <ID> <CEFR> [URL]")
    sys.exit(1)

assessment_id = sys.argv[1]
cefr = sys.argv[2]
url = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_URL

payload = {"assessmentInstanceId": assessment_id,"cefr": cefr, "retryCount": 0, "startTime": None}
data = base64.b64encode(json.dumps(payload).encode()).decode()
body = json.dumps({"message": {"data": data}}).encode()

endpoint = f"{url}/edspeak/grade"
print(f"POST {endpoint}  ID={assessment_id}  CEFR={cefr}")
try:
    req = Request(endpoint, 
                  data=body, 
                  headers={"Content-Type": "application/json"}, 
                  method="POST",
)
    with urlopen(req) as r:
        print(r.read().decode())
except URLError as e:
    print(f"Connection error: {e.reason}")
    sys.exit(1)
