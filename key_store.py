from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
import secrets
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://Damandeep:MongoDB@cluster0.9j661l9.mongodb.net/axigrade?retryWrites=true&w=majority&appName=Cluster0")
AGENT_NAME = "seo-tags"

_client = None
_col = None

def _get_col():
    global _client, _col
    if _col is None:
        _client = MongoClient(MONGO_URI)
        db = _client["axigrade"]
        _col = db["api_keys"]
        # Unique index on (user_id, agent) — safe to call repeatedly
        _col.create_index([("user_id", 1), ("agent", 1)], unique=True)
        _col.create_index("key", unique=True)
    return _col


def generate_key(user_id: str) -> dict:
    """Create a new API key for user_id under the seo-tags agent.
    Raises DuplicateKeyError if the user already has a key for this agent."""
    col = _get_col()
    key = "axg_" + secrets.token_hex(24)
    doc = {
        "key":        key,
        "user_id":    user_id,
        "agent":      AGENT_NAME,
        "credits":    25,
        "call_count": 0,
        "is_active":  True,
    }
    col.insert_one(doc)
    return {"key": key, "user_id": user_id, "agent": AGENT_NAME, "credits": 25}


def validate_and_deduct(api_key: str) -> tuple[bool, str]:
    """
    Validates the key and deducts 1 credit atomically.
    Returns (True, user_id) on success, (False, reason) on failure.
    """
    col = _get_col()
    doc = col.find_one({"key": api_key, "agent": AGENT_NAME})

    if not doc:
        return False, "Invalid API key"
    if not doc.get("is_active"):
        return False, "API key is inactive"
    if doc.get("credits", 0) <= 0:
        return False, "Insufficient credits"

    # Atomic deduct
    col.update_one(
        {"key": api_key},
        {"$inc": {"credits": -1, "call_count": 1}}
    )
    return True, doc["user_id"]


def get_key_info(api_key: str) -> dict | None:
    col = _get_col()
    doc = col.find_one({"key": api_key, "agent": AGENT_NAME}, {"_id": 0})
    return doc