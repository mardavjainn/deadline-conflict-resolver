"""
Flask REST API for the Deadline Conflict Resolver.

Endpoints
---------
GET  /api/health                – health check
GET  /api/tasks                 – list all tasks
POST /api/tasks                 – create a task
PUT  /api/tasks/<id>            – update a task
DELETE /api/tasks/<id>          – delete a task
POST /api/analyze/conflicts     – detect conflicts in submitted tasks
POST /api/analyze/workload      – analyze workload feasibility
POST /api/analyze/risk          – predict ML risk scores
POST /api/analyze/schedule      – generate optimized schedule
POST /api/analyze/full          – run all analyses in one call
"""

import sys
import os
import uuid
from datetime import datetime, timezone
from typing import Dict

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Ensure the backend package root is on the path when running from any CWD
sys.path.insert(0, os.path.dirname(__file__))

from models.task import Task
from services.conflict_detector import detect_conflicts
from services.workload_analyzer import analyze_workload
from services.ml_predictor import predict_risk
from services.scheduler import generate_schedule

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)

# ---------------------------------------------------------------------------
# In-memory task store (reset on server restart)
# ---------------------------------------------------------------------------
_tasks: Dict[str, Task] = {}


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _parse_tasks_from_request() -> list:
    """Parse a list of task dicts from the current JSON request body."""
    data = request.get_json(force=True, silent=True) or {}
    raw_tasks = data.get("tasks", [])
    return [Task.from_dict(t) for t in raw_tasks]


def _error(message: str, status: int = 400):
    return jsonify({"error": message}), status


# ---------------------------------------------------------------------------
# Frontend serving
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now(tz=timezone.utc).isoformat()})


# ---------------------------------------------------------------------------
# Task CRUD
# ---------------------------------------------------------------------------

@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    return jsonify([t.to_dict() for t in _tasks.values()])


@app.route("/api/tasks", methods=["POST"])
def create_task():
    data = request.get_json(force=True, silent=True)
    if not data:
        return _error("Request body must be JSON.")
    data.setdefault("id", str(uuid.uuid4()))
    try:
        task = Task.from_dict(data)
    except (KeyError, ValueError) as exc:
        return _error(f"Invalid task data: {exc}")
    _tasks[task.id] = task
    return jsonify(task.to_dict()), 201


@app.route("/api/tasks/<task_id>", methods=["PUT"])
def update_task(task_id: str):
    if task_id not in _tasks:
        return _error("Task not found.", 404)
    data = request.get_json(force=True, silent=True)
    if not data:
        return _error("Request body must be JSON.")
    data["id"] = task_id
    try:
        task = Task.from_dict(data)
    except (KeyError, ValueError) as exc:
        return _error(f"Invalid task data: {exc}")
    _tasks[task_id] = task
    return jsonify(task.to_dict())


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id: str):
    if task_id not in _tasks:
        return _error("Task not found.", 404)
    del _tasks[task_id]
    return jsonify({"deleted": task_id})


# ---------------------------------------------------------------------------
# Analysis endpoints
# ---------------------------------------------------------------------------

@app.route("/api/analyze/conflicts", methods=["POST"])
def analyze_conflicts():
    try:
        tasks = _parse_tasks_from_request()
    except Exception as exc:
        return _error(f"Invalid request: {exc}")
    conflicts = detect_conflicts(tasks)
    return jsonify({"conflicts": conflicts, "count": len(conflicts)})


@app.route("/api/analyze/workload", methods=["POST"])
def analyze_workload_endpoint():
    try:
        tasks = _parse_tasks_from_request()
    except Exception as exc:
        return _error(f"Invalid request: {exc}")
    result = analyze_workload(tasks)
    return jsonify(result)


@app.route("/api/analyze/risk", methods=["POST"])
def analyze_risk():
    try:
        tasks = _parse_tasks_from_request()
    except Exception as exc:
        return _error(f"Invalid request: {exc}")
    predictions = predict_risk(tasks)
    return jsonify({"predictions": predictions})


@app.route("/api/analyze/schedule", methods=["POST"])
def analyze_schedule():
    try:
        tasks = _parse_tasks_from_request()
    except Exception as exc:
        return _error(f"Invalid request: {exc}")
    result = generate_schedule(tasks)
    return jsonify(result)


@app.route("/api/analyze/full", methods=["POST"])
def analyze_full():
    """Run conflict detection, workload analysis, risk prediction, and scheduling."""
    try:
        tasks = _parse_tasks_from_request()
    except Exception as exc:
        return _error(f"Invalid request: {exc}")

    conflicts = detect_conflicts(tasks)
    workload = analyze_workload(tasks)
    risk = predict_risk(tasks)
    schedule = generate_schedule(tasks)

    return jsonify(
        {
            "conflicts": {"items": conflicts, "count": len(conflicts)},
            "workload": workload,
            "risk": {"predictions": risk},
            "schedule": schedule,
        }
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
