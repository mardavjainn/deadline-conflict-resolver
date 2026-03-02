"""Tests for the ML risk predictor service."""

import sys
import os
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.task import Task
from services.ml_predictor import predict_risk, RandomForestClassifier, _generate_training_data


def _make_task(task_id, title, days_ahead, estimated_hours, priority=3):
    deadline = datetime.now() + timedelta(days=days_ahead)
    return Task(
        id=task_id,
        title=title,
        deadline=deadline,
        estimated_hours=estimated_hours,
        priority=priority,
    )


class TestPredictRisk:
    def test_empty_tasks_returns_empty(self):
        assert predict_risk([]) == []

    def test_returns_one_result_per_task(self):
        tasks = [
            _make_task("t1", "Task A", 10, 5),
            _make_task("t2", "Task B", 3, 20),
        ]
        results = predict_risk(tasks)
        assert len(results) == 2

    def test_result_fields_present(self):
        task = _make_task("t1", "Task", 5, 8)
        result = predict_risk([task])[0]
        assert "task_id" in result
        assert "task_title" in result
        assert "risk_score" in result
        assert "risk_level" in result
        assert "features" in result

    def test_risk_score_in_valid_range(self):
        tasks = [_make_task(f"t{i}", f"Task {i}", 10, 5 * i) for i in range(1, 5)]
        for r in predict_risk(tasks):
            assert 0.0 <= r["risk_score"] <= 1.0

    def test_risk_level_valid_values(self):
        tasks = [_make_task(f"t{i}", f"Task {i}", 10, 5 * i) for i in range(1, 5)]
        for r in predict_risk(tasks):
            assert r["risk_level"] in ("low", "medium", "high")

    def test_high_urgency_task_has_higher_risk(self):
        # Task with very tight deadline should have higher risk than relaxed task
        urgent = _make_task("urgent", "Urgent", days_ahead=1, estimated_hours=20)
        relaxed = _make_task("relaxed", "Relaxed", days_ahead=30, estimated_hours=4)
        results = predict_risk([urgent, relaxed])
        urgent_risk = next(r["risk_score"] for r in results if r["task_id"] == "urgent")
        relaxed_risk = next(r["risk_score"] for r in results if r["task_id"] == "relaxed")
        assert urgent_risk > relaxed_risk


class TestRandomForest:
    def test_training_data_balanced(self):
        X, y = _generate_training_data(n_samples=500)
        assert len(X) == 500
        assert len(y) == 500
        pos_rate = sum(y) / len(y)
        assert 0.2 < pos_rate < 0.8  # not extremely skewed

    def test_classifier_trains_and_predicts(self):
        X, y = _generate_training_data(n_samples=200)
        clf = RandomForestClassifier(n_estimators=10, max_depth=4, random_seed=0)
        clf.fit(X, y)
        probs = clf.predict_proba(X[:10])
        assert len(probs) == 10
        for p in probs:
            assert 0.0 <= p <= 1.0
