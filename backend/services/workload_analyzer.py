"""Workload feasibility analysis service."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from models.task import Task


DAILY_HOURS_AVAILABLE = 8.0
WEEKLY_HOURS_AVAILABLE = DAILY_HOURS_AVAILABLE * 5  # Mon–Fri


def analyze_workload(
    tasks: List[Task], reference_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Analyze the feasibility of completing all tasks given their deadlines.

    Returns a summary dict containing:
      - total_estimated_hours: sum of all task hours
      - total_available_hours: working hours available before the last deadline
      - utilization_rate: ratio of required to available hours (0.0–∞)
      - is_feasible: True when utilization_rate <= 1.0
      - overloaded_periods: list of daily/weekly periods exceeding capacity
      - task_breakdown: per-task feasibility metrics
    """
    reference = reference_date or datetime.now()

    if not tasks:
        return {
            "total_estimated_hours": 0,
            "total_available_hours": 0,
            "utilization_rate": 0.0,
            "is_feasible": True,
            "overloaded_periods": [],
            "task_breakdown": [],
        }

    total_hours = sum(t.estimated_hours for t in tasks)
    horizon_days = max(
        (max(int(t.days_until_deadline(reference)), 0) for t in tasks), default=0
    )
    # Count working days (Mon–Fri) in the horizon
    working_days = _count_working_days(reference, horizon_days)
    total_available = working_days * DAILY_HOURS_AVAILABLE
    utilization = total_hours / total_available if total_available > 0 else float("inf")

    overloaded = _find_overloaded_periods(tasks, reference)

    task_breakdown = []
    for task in tasks:
        days_left = task.days_until_deadline(reference)
        working_days_left = _count_working_days(reference, max(int(days_left), 0))
        available_for_task = working_days_left * DAILY_HOURS_AVAILABLE
        task_util = (
            task.estimated_hours / available_for_task if available_for_task > 0 else float("inf")
        )
        task_breakdown.append(
            {
                "task_id": task.id,
                "task_title": task.title,
                "estimated_hours": task.estimated_hours,
                "days_until_deadline": round(days_left, 1),
                "working_days_until_deadline": working_days_left,
                "hours_available": round(available_for_task, 1),
                "utilization_rate": round(task_util, 3),
                "is_feasible": task_util <= 1.0,
            }
        )

    return {
        "total_estimated_hours": round(total_hours, 2),
        "total_available_hours": round(total_available, 2),
        "utilization_rate": round(utilization, 3),
        "is_feasible": utilization <= 1.0,
        "overloaded_periods": overloaded,
        "task_breakdown": task_breakdown,
    }


def _count_working_days(reference: datetime, days_ahead: int) -> int:
    """Count Mon–Fri working days within the next ``days_ahead`` days."""
    count = 0
    for offset in range(days_ahead):
        day = (reference + timedelta(days=offset)).weekday()
        if day < 5:  # 0=Mon … 4=Fri
            count += 1
    return count


def _find_overloaded_periods(
    tasks: List[Task], reference: datetime
) -> List[Dict[str, Any]]:
    """Return a list of daily periods where required hours exceed capacity."""
    daily: Dict[str, float] = {}
    for task in tasks:
        days_left = task.days_until_deadline(reference)
        if days_left <= 0:
            continue
        work_days = max(int(days_left), 1)
        hours_per_day = task.estimated_hours / work_days
        for offset in range(work_days):
            day = reference + timedelta(days=offset)
            if day.weekday() < 5:
                key = day.date().isoformat()
                daily[key] = daily.get(key, 0.0) + hours_per_day

    overloaded = []
    for day_str, load in sorted(daily.items()):
        if load > DAILY_HOURS_AVAILABLE:
            overloaded.append(
                {
                    "date": day_str,
                    "hours_required": round(load, 2),
                    "hours_available": DAILY_HOURS_AVAILABLE,
                    "overflow_hours": round(load - DAILY_HOURS_AVAILABLE, 2),
                }
            )
    return overloaded
