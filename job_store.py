"""
JobStore — MongoDB backed
Saves to axigrade.jobs collection (same as script generator).
Schema: job_id, status, created_at, updated_at, result, error
"""

from datetime import datetime, timezone
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://Damandeep:MongoDB@cluster0.9j661l9.mongodb.net/axigrade?retryWrites=true&w=majority&appName=Cluster0")

_client = None
_col = None

def _get_col():
    global _client, _col
    if _col is None:
        _client = MongoClient(MONGO_URI)
        db = _client["axigrade"]
        _col = db["jobs"]
        _col.create_index("job_id", unique=True)
    return _col

# Max 20 concurrent SEO jobs
_executor = ThreadPoolExecutor(max_workers=20)


class JobStore:

    def create(self, job_id: str) -> dict:
        job = {
            "job_id":     job_id,
            "status":     "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "result":     None,
            "error":      None,
        }
        _get_col().insert_one({**job})
        return job

    def set_running(self, job_id: str):
        _get_col().update_one(
            {"job_id": job_id},
            {"$set": {"status": "running", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )

    def set_done(self, job_id: str, result: dict):
        _get_col().update_one(
            {"job_id": job_id},
            {"$set": {"status": "done", "result": result, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )

    def set_failed(self, job_id: str, error: str):
        _get_col().update_one(
            {"job_id": job_id},
            {"$set": {"status": "failed", "error": error, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )

    def get(self, job_id: str) -> Optional[dict]:
        doc = _get_col().find_one({"job_id": job_id}, {"_id": 0})
        return doc


# Singleton
job_store = JobStore()


def create_job(job_id: str) -> dict:
    return job_store.create(job_id)


def run_job(job_id: str, fn, *args, **kwargs):
    def _run():
        job_store.set_running(job_id)
        try:
            result = fn(*args, **kwargs)
            job_store.set_done(job_id, result)
        except Exception as e:
            job_store.set_failed(job_id, str(e))
    _executor.submit(_run)


def get_job(job_id: str) -> Optional[dict]:
    return job_store.get(job_id)