"""Deadline conflict detection service."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from models.task import Task


# Maximum working hours per day available for tasks
DAILY_HOURS_AVAILABLE = 8.0


def detect_conflicts(tasks: List[Task], reference_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    Detect deadline conflicts among a list of tasks.

    A conflict is reported when:
      - A task is already overdue.
      - Two or more tasks share the same deadline and cannot both be completed
        within the available hours for that day.
      - The total required hours in any single day exceeds the available capacity.

    Returns a list of conflict dictionaries describing each detected conflict.
    """
    reference = reference_date or datetime.now()
    conflicts: List[Dict[str, Any]] = []

    # Bucket tasks by deadline date (date only, not time)
    deadline_buckets: Dict[str, List[Task]] = {}
    for task in tasks:
        if task.is_overdue(reference):
            conflicts.append(
                {
                    "type": "overdue",
                    "task_id": task.id,
                    "task_title": task.title,
                    "message": f"Task '{task.title}' is overdue (deadline: {task.deadline.date()}).",
                    "severity": "high",
                }
            )
        key = task.deadline.date().isoformat()
        deadline_buckets.setdefault(key, []).append(task)

    # Check for same-day deadline overload
    for date_str, bucket in deadline_buckets.items():
        if len(bucket) > 1:
            total_hours = sum(t.estimated_hours for t in bucket)
            if total_hours > DAILY_HOURS_AVAILABLE:
                task_titles = [t.title for t in bucket]
                conflicts.append(
                    {
                        "type": "deadline_overload",
                        "date": date_str,
                        "task_ids": [t.id for t in bucket],
                        "task_titles": task_titles,
                        "total_hours_required": total_hours,
                        "hours_available": DAILY_HOURS_AVAILABLE,
                        "message": (
                            f"Tasks {task_titles} all due on {date_str} require "
                            f"{total_hours:.1f}h but only {DAILY_HOURS_AVAILABLE:.1f}h available."
                        ),
                        "severity": "high",
                    }
                )

    # Check daily capacity over the planning horizon
    horizon_days = _planning_horizon_days(tasks, reference)
    daily_load: Dict[str, float] = _compute_daily_load(tasks, reference, horizon_days)
    for day_str, load in daily_load.items():
        if load > DAILY_HOURS_AVAILABLE:
            conflicts.append(
                {
                    "type": "capacity_overload",
                    "date": day_str,
                    "hours_required": round(load, 2),
                    "hours_available": DAILY_HOURS_AVAILABLE,
                    "message": (
                        f"Day {day_str} requires {load:.1f}h of work but only "
                        f"{DAILY_HOURS_AVAILABLE:.1f}h are available."
                    ),
                    "severity": "medium",
                }
            )

    return conflicts


def _planning_horizon_days(tasks: List[Task], reference: datetime) -> int:
    """Return the number of days from now to the furthest deadline."""
    if not tasks:
        return 0
    max_days = max(
        max(int(t.days_until_deadline(reference)) + 1, 0) for t in tasks
    )
    return max_days


def _compute_daily_load(
    tasks: List[Task], reference: datetime, horizon_days: int
) -> Dict[str, float]:
    """
    Spread each task's work evenly across the days remaining before its deadline.
    Returns a mapping of date string -> total hours required that day.
    """
    daily: Dict[str, float] = {}
    for task in tasks:
        days_left = task.days_until_deadline(reference)
        if days_left <= 0:
            continue
        work_days = max(int(days_left), 1)
        hours_per_day = task.estimated_hours / work_days
        for offset in range(work_days):
            day = (reference + timedelta(days=offset)).date().isoformat()
            daily[day] = daily.get(day, 0.0) + hours_per_day
    return daily
