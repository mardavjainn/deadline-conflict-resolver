"""
ML-based deadline failure risk predictor.

Uses a Random Forest classifier trained on synthetic task data to predict
the probability that a task will miss its deadline.

Features used:
  - days_until_deadline      : calendar days remaining
  - estimated_hours          : total effort required
  - hours_per_day_required   : effort / days_left
  - priority                 : task priority (1–5)
  - concurrent_tasks         : number of tasks active at the same time
  - utilization_rate         : hours_per_day_required / DAILY_HOURS_AVAILABLE
"""

import math
import random
from datetime import datetime
from typing import List, Dict, Any, Optional

from models.task import Task

DAILY_HOURS_AVAILABLE = 8.0

# ---------------------------------------------------------------------------
# Lightweight pure-Python Random Forest implementation
# (avoids a dependency on scikit-learn / numpy in environments where they
#  may not be installed; produces robust predictions for the feature space.)
# ---------------------------------------------------------------------------


def _gini(labels: List[int]) -> float:
    """Compute Gini impurity for a list of binary labels."""
    n = len(labels)
    if n == 0:
        return 0.0
    p1 = sum(labels) / n
    return 1.0 - p1 ** 2 - (1.0 - p1) ** 2


def _best_split(X: List[List[float]], y: List[int], feature_indices: List[int]):
    """Find the best (feature, threshold) split minimising weighted Gini impurity."""
    best_gain = -1.0
    best_feat = None
    best_thresh = None
    base_gini = _gini(y)
    n = len(y)

    for fi in feature_indices:
        values = sorted(set(row[fi] for row in X))
        for i in range(len(values) - 1):
            thresh = (values[i] + values[i + 1]) / 2.0
            left_y = [y[j] for j in range(n) if X[j][fi] <= thresh]
            right_y = [y[j] for j in range(n) if X[j][fi] > thresh]
            if not left_y or not right_y:
                continue
            weighted = (len(left_y) * _gini(left_y) + len(right_y) * _gini(right_y)) / n
            gain = base_gini - weighted
            if gain > best_gain:
                best_gain, best_feat, best_thresh = gain, fi, thresh

    return best_feat, best_thresh


def _build_tree(
    X: List[List[float]],
    y: List[int],
    feature_indices: List[int],
    max_depth: int,
    min_samples: int,
    depth: int = 0,
) -> dict:
    """Recursively build a decision tree node."""
    n_pos = sum(y)
    n = len(y)
    leaf_prob = n_pos / n if n > 0 else 0.0

    if depth >= max_depth or n < min_samples or len(set(y)) == 1:
        return {"leaf": True, "prob": leaf_prob}

    feat, thresh = _best_split(X, y, feature_indices)
    if feat is None:
        return {"leaf": True, "prob": leaf_prob}

    left_idx = [j for j in range(n) if X[j][feat] <= thresh]
    right_idx = [j for j in range(n) if X[j][feat] > thresh]

    if not left_idx or not right_idx:
        return {"leaf": True, "prob": leaf_prob}

    left_X = [X[j] for j in left_idx]
    left_y = [y[j] for j in left_idx]
    right_X = [X[j] for j in right_idx]
    right_y = [y[j] for j in right_idx]

    return {
        "leaf": False,
        "feature": feat,
        "threshold": thresh,
        "left": _build_tree(left_X, left_y, feature_indices, max_depth, min_samples, depth + 1),
        "right": _build_tree(right_X, right_y, feature_indices, max_depth, min_samples, depth + 1),
    }


def _predict_tree(tree: dict, x: List[float]) -> float:
    """Traverse a decision tree and return the leaf probability."""
    if tree["leaf"]:
        return tree["prob"]
    if x[tree["feature"]] <= tree["threshold"]:
        return _predict_tree(tree["left"], x)
    return _predict_tree(tree["right"], x)


class RandomForestClassifier:
    """Minimal Random Forest for binary classification."""

    def __init__(
        self,
        n_estimators: int = 50,
        max_depth: int = 6,
        min_samples_split: int = 4,
        max_features: int = 4,
        random_seed: int = 42,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.max_features = max_features
        self._trees: List[dict] = []
        self._rng = random.Random(random_seed)

    def fit(self, X: List[List[float]], y: List[int]) -> None:
        """Train the forest on feature matrix X and labels y."""
        n = len(X)
        n_features = len(X[0]) if X else 0
        max_feat = min(self.max_features, n_features)

        self._trees = []
        for _ in range(self.n_estimators):
            # Bootstrap sample
            indices = [self._rng.randint(0, n - 1) for _ in range(n)]
            boot_X = [X[i] for i in indices]
            boot_y = [y[i] for i in indices]

            # Random feature subset
            feat_indices = self._rng.sample(range(n_features), max_feat)

            tree = _build_tree(
                boot_X,
                boot_y,
                feat_indices,
                self.max_depth,
                self.min_samples_split,
            )
            self._trees.append(tree)

    def predict_proba(self, X: List[List[float]]) -> List[float]:
        """Return the mean positive-class probability across all trees."""
        results = []
        for x in X:
            probs = [_predict_tree(t, x) for t in self._trees]
            results.append(sum(probs) / len(probs) if probs else 0.5)
        return results


# ---------------------------------------------------------------------------
# Synthetic training data generator
# ---------------------------------------------------------------------------

def _generate_training_data(n_samples: int = 2000, seed: int = 42):
    """
    Generate synthetic training samples for the risk predictor.

    Label = 1 (high risk / likely to fail) when the task is under time pressure.
    """
    rng = random.Random(seed)
    X: List[List[float]] = []
    y: List[int] = []

    for _ in range(n_samples):
        days = rng.uniform(0.5, 60)
        hours = rng.uniform(1, 80)
        priority = rng.randint(1, 5)
        concurrent = rng.randint(0, 10)

        hpd = hours / max(days, 0.1)
        util = hpd / DAILY_HOURS_AVAILABLE
        norm_days = min(days / 60, 1.0)
        norm_hours = min(hours / 80, 1.0)

        features = [days, hours, hpd, priority, concurrent, util]

        # Risk heuristic used to label synthetic data
        risk_score = (
            0.40 * min(util, 3.0) / 3.0
            + 0.25 * (1.0 - norm_days)
            + 0.15 * norm_hours
            + 0.10 * (concurrent / 10.0)
            + 0.10 * (priority / 5.0)
        )
        noise = rng.gauss(0, 0.08)
        label = 1 if (risk_score + noise) > 0.45 else 0

        X.append(features)
        y.append(label)

    return X, y


# ---------------------------------------------------------------------------
# Module-level singleton (trained once on import)
# ---------------------------------------------------------------------------

_MODEL: Optional[RandomForestClassifier] = None


def _get_model() -> RandomForestClassifier:
    global _MODEL
    if _MODEL is None:
        X_train, y_train = _generate_training_data()
        clf = RandomForestClassifier(n_estimators=50, max_depth=6, random_seed=42)
        clf.fit(X_train, y_train)
        _MODEL = clf
    return _MODEL


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def predict_risk(
    tasks: List[Task],
    reference_date: Optional[datetime] = None,
    concurrent_count: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Predict the deadline-failure risk for each task.

    Parameters
    ----------
    tasks           : list of Task objects to evaluate
    reference_date  : evaluation reference date (defaults to now)
    concurrent_count: override number of concurrent tasks (defaults to len(tasks))

    Returns a list of dicts with keys:
      task_id, task_title, risk_score (0.0–1.0), risk_level, features
    """
    reference = reference_date or datetime.now()
    model = _get_model()
    n_concurrent = concurrent_count if concurrent_count is not None else len(tasks)

    results: List[Dict[str, Any]] = []
    if not tasks:
        return results

    feature_matrix: List[List[float]] = []
    for task in tasks:
        days = max(task.days_until_deadline(reference), 0.0)
        hours = task.estimated_hours
        hpd = hours / max(days, 0.1)
        util = hpd / DAILY_HOURS_AVAILABLE
        features = [days, hours, hpd, float(task.priority), float(n_concurrent), util]
        feature_matrix.append(features)

    probabilities = model.predict_proba(feature_matrix)

    for task, prob, feats in zip(tasks, probabilities, feature_matrix):
        days, hours, hpd, priority, concurrent, util = feats
        risk_score = round(prob, 4)
        if risk_score >= 0.70:
            risk_level = "high"
        elif risk_score >= 0.40:
            risk_level = "medium"
        else:
            risk_level = "low"

        results.append(
            {
                "task_id": task.id,
                "task_title": task.title,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "features": {
                    "days_until_deadline": round(days, 2),
                    "estimated_hours": hours,
                    "hours_per_day_required": round(hpd, 3),
                    "priority": int(priority),
                    "concurrent_tasks": int(concurrent),
                    "utilization_rate": round(util, 3),
                },
            }
        )

    return results
