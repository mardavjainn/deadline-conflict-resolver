"""Tests for the conflict detection service."""

import sys
import os
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.task import Task
from services.conflict_detector import detect_conflicts, DAILY_HOURS_AVAILABLE


def _make_task(task_id, title, days_ahead, estimated_hours, priority=3):
    deadline = datetime.now() + timedelta(days=days_ahead)
    return Task(
        id=task_id,
        title=title,
        deadline=deadline,
        estimated_hours=estimated_hours,
        priority=priority,
    )


class TestDetectConflicts:
    def test_no_tasks_returns_empty(self):
        assert detect_conflicts([]) == []

    def test_single_feasible_task_no_conflict(self):
        task = _make_task("t1", "Write report", days_ahead=10, estimated_hours=4)
        conflicts = detect_conflicts([task])
        assert conflicts == []

    def test_overdue_task_detected(self):
        task = _make_task("t1", "Old task", days_ahead=-1, estimated_hours=3)
        conflicts = detect_conflicts([task])
        overdue = [c for c in conflicts if c["type"] == "overdue"]
        assert len(overdue) == 1
        assert overdue[0]["task_id"] == "t1"
        assert overdue[0]["severity"] == "high"

    def test_same_day_deadline_overload(self):
        # Two tasks both due tomorrow, total hours > 8
        tomorrow = datetime.now() + timedelta(days=1)
        t1 = Task("t1", "Task A", tomorrow, estimated_hours=5, priority=3)
        t2 = Task("t2", "Task B", tomorrow, estimated_hours=5, priority=3)
        conflicts = detect_conflicts([t1, t2])
        overload = [c for c in conflicts if c["type"] == "deadline_overload"]
        assert len(overload) == 1
        assert overload[0]["total_hours_required"] == 10

    def test_no_overload_when_hours_fit(self):
        tomorrow = datetime.now() + timedelta(days=1)
        t1 = Task("t1", "Task A", tomorrow, estimated_hours=3, priority=3)
        t2 = Task("t2", "Task B", tomorrow, estimated_hours=4, priority=3)
        conflicts = detect_conflicts([t1, t2])
        overload = [c for c in conflicts if c["type"] == "deadline_overload"]
        assert overload == []

    def test_capacity_overload_detected_for_heavy_workload(self):
        # One task with massive hours due very soon → capacity overload
        task = _make_task("t1", "Big project", days_ahead=3, estimated_hours=40)
        conflicts = detect_conflicts([task])
        capacity_issues = [c for c in conflicts if c["type"] == "capacity_overload"]
        assert len(capacity_issues) > 0

    def test_multiple_overdue_tasks(self):
        t1 = _make_task("t1", "A", days_ahead=-2, estimated_hours=2)
        t2 = _make_task("t2", "B", days_ahead=-1, estimated_hours=3)
        conflicts = detect_conflicts([t1, t2])
        overdue_ids = {c["task_id"] for c in conflicts if c["type"] == "overdue"}
        assert "t1" in overdue_ids
        assert "t2" in overdue_ids
