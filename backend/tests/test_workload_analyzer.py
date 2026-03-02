"""Tests for the workload feasibility analysis service."""

import sys
import os
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.task import Task
from services.workload_analyzer import analyze_workload, DAILY_HOURS_AVAILABLE


def _make_task(task_id, title, days_ahead, estimated_hours, priority=3):
    deadline = datetime.now() + timedelta(days=days_ahead)
    return Task(
        id=task_id,
        title=title,
        deadline=deadline,
        estimated_hours=estimated_hours,
        priority=priority,
    )


class TestAnalyzeWorkload:
    def test_empty_task_list(self):
        result = analyze_workload([])
        assert result["total_estimated_hours"] == 0
        assert result["is_feasible"] is True
        assert result["utilization_rate"] == 0.0

    def test_single_feasible_task(self):
        task = _make_task("t1", "Small task", days_ahead=10, estimated_hours=4)
        result = analyze_workload([task])
        assert result["total_estimated_hours"] == 4
        assert result["is_feasible"] is True
        assert result["utilization_rate"] < 1.0

    def test_infeasible_workload(self):
        # 80 hours due in 2 days → infeasible
        task = _make_task("t1", "Huge task", days_ahead=2, estimated_hours=80)
        result = analyze_workload([task])
        assert result["is_feasible"] is False
        assert result["utilization_rate"] > 1.0

    def test_task_breakdown_present(self):
        task = _make_task("t1", "Report", days_ahead=5, estimated_hours=8)
        result = analyze_workload([task])
        assert len(result["task_breakdown"]) == 1
        breakdown = result["task_breakdown"][0]
        assert breakdown["task_id"] == "t1"
        assert "utilization_rate" in breakdown
        assert "is_feasible" in breakdown

    def test_utilization_rate_correct(self):
        # 16 hours over 10 working days (80 available) → ~0.20 utilization
        task = _make_task("t1", "Task", days_ahead=14, estimated_hours=16)
        result = analyze_workload([task])
        assert result["utilization_rate"] < 0.5

    def test_overloaded_periods_reported(self):
        # Dense workload should generate overloaded period entries
        task = _make_task("t1", "Crunch", days_ahead=3, estimated_hours=40)
        result = analyze_workload([task])
        assert len(result["overloaded_periods"]) > 0

    def test_multiple_tasks_sum_correctly(self):
        t1 = _make_task("t1", "A", days_ahead=20, estimated_hours=10)
        t2 = _make_task("t2", "B", days_ahead=20, estimated_hours=15)
        result = analyze_workload([t1, t2])
        assert result["total_estimated_hours"] == 25
