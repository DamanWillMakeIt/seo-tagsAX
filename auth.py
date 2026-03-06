from functools import wraps
from flask import request, jsonify
from key_store import validate_and_deduct


def require_api_key(f):
    """Decorator — validates X-API-Key header and deducts 1 credit."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return jsonify({"error": "Missing X-API-Key header"}), 401

        valid, result = validate_and_deduct(api_key)

        if not valid:
            status = 402 if result == "Insufficient credits" else 401
            return jsonify({"error": result}), status

        # Attach user_id to request context so routes can use it if needed
        request.user_id = result
        return f(*args, **kwargs)

    return decorated