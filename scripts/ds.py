"""
Datastore utility — run from project root.

Usage:
  python scripts/ds.py list
  python scripts/ds.py count
  python scripts/ds.py clear
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import PROJECT_ID, DATASTORE_DATABASE_ID, GRADING_STATUS_KIND, NAMESPACE
from google.cloud import datastore


def get_client():
    return datastore.Client(project=PROJECT_ID, namespace=NAMESPACE, database=DATASTORE_DATABASE_ID)


def cmd_count():
    c = get_client()
    n = len(list(c.query(kind=GRADING_STATUS_KIND).fetch()))
    print(f"{n} records in '{GRADING_STATUS_KIND}'")


def cmd_list():
    c = get_client()
    entities = list(c.query(kind=GRADING_STATUS_KIND).fetch())
    if not entities:
        print("No records found.")
        return
    print(f"{'ID':<30} {'status':<12} updated_at")
    print("-" * 70)
    for e in entities:
        print(f"{e.key.name:<30} {e.get('status', '?'):<12} {e.get('updated_at', '-')}")


def cmd_clear():
    c = get_client()
    keys = [e.key for e in c.query(kind=GRADING_STATUS_KIND).fetch()]
    if not keys:
        print("Nothing to delete.")
        return
    confirm = input(f"Delete {len(keys)} records? [y/N] ")
    if confirm.lower() != "y":
        print("Aborted.")
        return
    c.delete_multi(keys)
    print(f"Deleted {len(keys)} records.")


COMMANDS = {"count": cmd_count, "list": cmd_list, "clear": cmd_clear}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: python scripts/ds.py [{' | '.join(COMMANDS)}]")
        sys.exit(1)
    COMMANDS[sys.argv[1]]()
