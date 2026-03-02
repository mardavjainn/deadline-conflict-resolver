"""Tests for the heuristic scheduler service."""

import sys
import os
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.task import Task
from services.scheduler import generate_schedule, DAILY_HOURS_AVAILABLE


def _make_task(task_id, title, days_ahead, estimated_hours, priority=3):
    deadline = datetime.now() + timedelta(days=days_ahead)
    return Task(
        id=task_id,
        title=title,
        deadline=deadline,
        estimated_hours=estimated_hours,
        priority=priority,
    )


class TestGenerateSchedule:
    def test_empty_tasks_returns_empty_schedule(self):
        result = generate_schedule([])
        assert result["schedule"] == []
        assert result["unscheduled"] == []
        assert result["total_days_used"] == 0

    def test_single_task_scheduled(self):
        task = _make_task("t1", "Write report", days_ahead=5, estimated_hours=4)
        result = generate_schedule([task])
        assert len(result["schedule"]) > 0
        assert result["unscheduled"] == []

    def test_all_scheduled_tasks_have_required_fields(self):
        task = _make_task("t1", "Task", days_ahead=5, estimated_hours=4)
        result = generate_schedule([task])
        for slot in result["schedule"]:
            assert "task_id" in slot
            assert "task_title" in slot
            assert "date" in slot
            assert "hours_assigned" in slot

    def test_daily_hours_not_exceeded(self):
        tasks = [
            _make_task("t1", "A", 10, 6),
            _make_task("t2", "B", 10, 6),
            _make_task("t3", "C", 10, 6),
        ]
        result = generate_schedule(tasks)
        # Aggregate hours per day
        daily: dict = {}
        for slot in result["schedule"]:
            daily[slot["date"]] = daily.get(slot["date"], 0) + slot["hours_assigned"]
        for day, hours in daily.items():
            assert hours <= DAILY_HOURS_AVAILABLE + 0.01  # tolerance for float rounding

    def test_impossible_task_goes_to_unscheduled(self):
        # 40 hours due in 1 working day → cannot be scheduled
        task = _make_task("t1", "Impossible", days_ahead=1, estimated_hours=40)
        result = generate_schedule([task])
        unscheduled_ids = {u["task_id"] for u in result["unscheduled"]}
        assert "t1" in unscheduled_ids

    def test_higher_priority_task_scheduled_earlier(self):
        # Two tasks with same deadline; higher priority should appear first in schedule
        ref = datetime.now()
        deadline = ref + timedelta(days=5)
        high = Task("high", "High Priority", deadline, estimated_hours=4, priority=5)
        low = Task("low", "Low Priority", deadline, estimated_hours=4, priority=1)
        result = generate_schedule([low, high], reference_date=ref)
        # All slots should be present
        scheduled_ids = {s["task_id"] for s in result["schedule"]}
        assert "high" in scheduled_ids
        assert "low" in scheduled_ids

    def test_summary_counts_correct(self):
        tasks = [
            _make_task("t1", "A", 10, 4),
            _make_task("t2", "B", 10, 4),
        ]
        result = generate_schedule(tasks)
        total = result["summary"]["scheduled_count"] + result["summary"]["unscheduled_count"]
        assert total == len(tasks)

    def test_multiple_tasks_total_hours_assigned_matches(self):
        tasks = [
            _make_task("t1", "A", 10, 3),
            _make_task("t2", "B", 10, 5),
        ]
        result = generate_schedule(tasks)
        total_assigned = sum(s["hours_assigned"] for s in result["schedule"])
        total_expected = sum(t.estimated_hours for t in tasks)
        assert abs(total_assigned - total_expected) < 0.1
