"""Tests for the Flask API endpoints."""

import sys
import os
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def _task_payload(days_ahead=10, hours=4, priority=3):
    deadline = (datetime.now() + timedelta(days=days_ahead)).isoformat()
    return {
        "id": "test-task-1",
        "title": "Test Task",
        "deadline": deadline,
        "estimated_hours": hours,
        "priority": priority,
        "description": "A test task",
    }


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"


class TestTaskCRUD:
    def test_list_tasks_initially_empty(self, client):
        resp = client.get("/api/tasks")
        assert resp.status_code == 200

    def test_create_task(self, client):
        payload = _task_payload()
        resp = client.post("/api/tasks", json=payload)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["title"] == "Test Task"
        assert "id" in data

    def test_create_task_missing_fields(self, client):
        resp = client.post("/api/tasks", json={"title": "Incomplete"})
        assert resp.status_code == 400

    def test_update_task(self, client):
        payload = _task_payload()
        create_resp = client.post("/api/tasks", json=payload)
        task_id = create_resp.get_json()["id"]
        updated = {**payload, "id": task_id, "title": "Updated Title"}
        resp = client.put(f"/api/tasks/{task_id}", json=updated)
        assert resp.status_code == 200
        assert resp.get_json()["title"] == "Updated Title"

    def test_delete_task(self, client):
        payload = _task_payload()
        create_resp = client.post("/api/tasks", json=payload)
        task_id = create_resp.get_json()["id"]
        resp = client.delete(f"/api/tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.get_json()["deleted"] == task_id

    def test_delete_nonexistent_task(self, client):
        resp = client.delete("/api/tasks/nonexistent-id")
        assert resp.status_code == 404


class TestAnalysisEndpoints:
    def _tasks_body(self, n=2):
        tasks = []
        for i in range(n):
            tasks.append({
                "id": f"t{i}",
                "title": f"Task {i}",
                "deadline": (datetime.now() + timedelta(days=5 + i * 3)).isoformat(),
                "estimated_hours": 4 + i,
                "priority": 3,
            })
        return {"tasks": tasks}

    def test_conflicts_endpoint(self, client):
        resp = client.post("/api/analyze/conflicts", json=self._tasks_body())
        assert resp.status_code == 200
        data = resp.get_json()
        assert "conflicts" in data
        assert "count" in data

    def test_workload_endpoint(self, client):
        resp = client.post("/api/analyze/workload", json=self._tasks_body())
        assert resp.status_code == 200
        data = resp.get_json()
        assert "is_feasible" in data
        assert "utilization_rate" in data

    def test_risk_endpoint(self, client):
        resp = client.post("/api/analyze/risk", json=self._tasks_body())
        assert resp.status_code == 200
        data = resp.get_json()
        assert "predictions" in data

    def test_schedule_endpoint(self, client):
        resp = client.post("/api/analyze/schedule", json=self._tasks_body())
        assert resp.status_code == 200
        data = resp.get_json()
        assert "schedule" in data
        assert "unscheduled" in data

    def test_full_analysis_endpoint(self, client):
        resp = client.post("/api/analyze/full", json=self._tasks_body())
        assert resp.status_code == 200
        data = resp.get_json()
        assert "conflicts" in data
        assert "workload" in data
        assert "risk" in data
        assert "schedule" in data

    def test_analysis_with_empty_tasks(self, client):
        resp = client.post("/api/analyze/full", json={"tasks": []})
        assert resp.status_code == 200
