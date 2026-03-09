# ps — Edspeak Grading Service

A Flask service that receives grading jobs via Google Cloud Pub/Sub, runs them with distributed deduplication via Cloud Datastore, and returns results to Cloud Run.

---

## Prerequisites

| Tool | Purpose |
|---|---|
| Python 3.11 | Runtime |
| [mise](https://mise.jdx.dev) | Task runner + Python version manager |
| Docker | Local container testing |
| `gcloud` CLI | GCP deployment |
| `.key.json` | GCP service account key (shared separately — never committed) |

Install mise: https://mise.jdx.dev/getting-started.html

---

## Setup

```bash
git clone https://github.com/MaiRajborirug/ps.git
cd ps

# Place .key.json in the project root (get this from your team lead)

export GOOGLE_APPLICATION_CREDENTIALS=.key.json
export NAMESPACE=dev   # or assess-prd for production
```

---

## Run locally

### Option A — plain Python
```bash
pip install -r requirements.txt
mise run dev           # runs python app.py on port 8877
```

### Option B — Docker
```bash
mise run build         # build image
mise run run-doc       # run container on port 8877 (mounts .key.json automatically)
```

Smoke test:
```bash
curl http://localhost:8877/foo
# → {"success": true, "data": "Hi Universe!"}
```

---

## Deploy to Cloud Run

First time only — create the Artifact Registry:
```bash
mise run setup-registry
```

Deploy (builds, pushes image, deploys to Cloud Run):
```bash
mise run deploy
```

Get the deployed URL:
```bash
gcloud run services describe ps-4feb-service --region=us-central1 --format='value(status.url)'
```

Stream live logs:
```bash
gcloud run logs tail ps-4feb-service --region=us-central1
```

---

## Testing

### `scripts/test_grade.py` — send a grading request

```bash
python scripts/test_grade.py <ID= int> <CEFR> <GCP URL>

CEFR = text or positive int (sleep time for grade background duration), default=60s

# Examples
python scripts/test_grade.py 2 B1                              # local, even ID
python scripts/test_grade.py 13 4200 B1                              # local, odd ID
python scripts/test_grade.py 2 B1 <URL> # remote
```

**CEFR controls simulated grading duration.** If CEFR is a positive integer string, it is used as sleep seconds. Otherwise the default is 60s.

```bash
python scripts/test_grade.py 2 50      # sleeps 50s
python scripts/test_grade.py 2 2000    # sleeps ~33 min
```

### `scripts/test_grade.py` output

```
POST http://localhost:8877/edspeak/grade  ID=2  CEFR=B1
{"success": true, "data": "[ACK] grading done for 2, attempt: 0"}
```

The script blocks until the server responds (which takes as long as the grading sleep). A 200 means grading completed or retry was queued. A 500 means the job was NACKed (another instance holds the lease, or a crash occurred).

---

### mise test tasks — convenience wrappers around the same script

```bash
mise run test-grade ID=2 CEFR=B1          # single grading request
mise run test-dedup ID=10                 # fires two concurrent requests for the same ID
mise run test-done-skip ID=2              # re-sends after done — should return 200 immediately
```

`test-dedup`: the second request should return 500 NACK because the first holds an active Datastore lease.

`test-done-skip`: once an ID is marked `done`, any further requests skip grading and ACK immediately without touching the grading thread.

---

### `scripts/ds.py` — inspect / clear Datastore records

```bash
python scripts/ds.py list    # print all grading-status records
python scripts/ds.py count   # count records
python scripts/ds.py clear   # interactively delete all records (asks confirmation)
```

Run from the project root. Useful for resetting state between test runs.

---

## mise task reference

| Command | What it does |
|---|---|
| `mise run dev` | Run `app.py` directly on port 8877 |
| `mise run build` | Build Docker image for linux/amd64 |
| `mise run run-doc` | Run Docker container on port 8877 with `.key.json` mounted |
| `mise run purge` | Stop and remove container + image |
| `mise run deploy` | Authenticate, build, push, and deploy to Cloud Run |
| `mise run setup-registry` | Create Artifact Registry (run once) |
| `mise run export-requirements` | Regenerate `requirements.txt` from the lock file |
| `mise run test-grade` | Send one grading POST (options: `ID=`, `CEFR=`, `BASE_URL=`) |
| `mise run test-dedup` | Fire two concurrent requests for the same ID |
| `mise run test-done-skip` | Re-send after grading is done — expects immediate 200 skip |

---

## Key environment variables

| Variable | Default | Notes |
|---|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | — | Path to `.key.json`. Required for all GCP calls. |
| `NAMESPACE` | `None` → dev config | Set to `assess-prd` for production |
| `PORT` | `8877` | Flask / gunicorn port |
| `GRADE_RETRY_TOPIC_ID` | `edspeak-grade-retry` | Pub/Sub topic for application-level retries |
