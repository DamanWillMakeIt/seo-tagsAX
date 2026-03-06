from flask import Flask, request, jsonify
from main import run_seo_agent
from key_store import generate_key, get_key_info
from auth import require_api_key
from job_store import create_job, run_job, get_job
from pymongo.errors import DuplicateKeyError

app = Flask(__name__)


# ── Generate API Key ──────────────────────────────────────────────────────────
@app.route('/seo/generate-key', methods=['POST'])
def generate_key_endpoint():
    data = request.get_json()
    if not data or not data.get("user_id"):
        return jsonify({"error": "user_id is required"}), 400
    try:
        result = generate_key(data["user_id"])
        return jsonify({"status": "success", **result})
    except DuplicateKeyError:
        return jsonify({"error": "A key for this user already exists for seo-tags agent"}), 409


# ── Check Key Info ────────────────────────────────────────────────────────────
@app.route('/seo/key-info', methods=['GET'])
@require_api_key
def key_info():
    info = get_key_info(request.headers.get("X-API-Key"))
    if not info:
        return jsonify({"error": "Key not found"}), 404
    info.pop("key", None)
    return jsonify(info)


# ── Submit SEO Job (returns job_id immediately) ───────────────────────────────
@app.route('/architect/seo', methods=['POST'])
@require_api_key
def seo_endpoint():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400

    import uuid
    job_id = str(uuid.uuid4())
    create_job(job_id)
    run_job(job_id, run_seo_agent, data)

    return jsonify({
        "status":   "queued",
        "job_id":   job_id,
        "poll_url": f"/seo/status/{job_id}"
    }), 202


# ── Poll Job Status ───────────────────────────────────────────────────────────
@app.route('/seo/status/<job_id>', methods=['GET'])
@require_api_key
def job_status(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job["status"] == "done":
        return jsonify({"status": "done", "result": job["result"]})
    elif job["status"] == "failed":
        return jsonify({"status": "failed", "error": job["error"]}), 500
    else:
        return jsonify({"status": job["status"]}), 202


if __name__ == '__main__':
    app.run(port=5000, debug=False)