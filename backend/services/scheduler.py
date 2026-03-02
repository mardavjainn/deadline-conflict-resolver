"""
Heuristic task scheduler.

Implements a priority-weighted Earliest Deadline First (EDF) scheduling
algorithm that:
  1. Sorts tasks by a composite score (deadline urgency + priority).
  2. Assigns each task to working-day time slots respecting daily capacity.
  3. Detects and reports tasks that cannot be scheduled before their deadline.

The schedule is returned as an ordered list of slot assignments so the frontend
can render a day-by-day Gantt-style view.
"""

import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from models.task import Task

DAILY_HOURS_AVAILABLE = 8.0


def generate_schedule(
    tasks: List[Task],
    reference_date: Optional[datetime] = None,
    daily_hours: float = DAILY_HOURS_AVAILABLE,
) -> Dict[str, Any]:
    """
    Generate an optimized schedule for the given tasks.

    Returns a dict with:
      - schedule: ordered list of slot dicts (task_id, date, hours_assigned)
      - unscheduled: tasks that could not be placed before their deadline
      - total_days_used: number of working days in the schedule
      - summary: high-level metrics
    """
    reference = reference_date or datetime.now()

    if not tasks:
        return {
            "schedule": [],
            "unscheduled": [],
            "total_days_used": 0,
            "summary": {"scheduled_count": 0, "unscheduled_count": 0},
        }

    # Sort tasks by composite urgency score (lower = more urgent)
    sorted_tasks = _sort_by_urgency(tasks, reference)

    schedule: List[Dict[str, Any]] = []
    unscheduled: List[Dict[str, Any]] = []

    # Remaining hours to assign per task
    remaining: Dict[str, float] = {t.id: t.estimated_hours for t in sorted_tasks}

    # Working-day capacity map: date_str -> hours_remaining
    capacity: Dict[str, float] = {}

    for task in sorted_tasks:
        hours_left = remaining[task.id]
        days_available = max(math.ceil(task.days_until_deadline(reference)), 1)

        assigned = 0.0
        for offset in range(days_available):
            if hours_left <= 0:
                break
            day = reference + timedelta(days=offset)
            if day.weekday() >= 5:  # skip weekends
                continue
            day_str = day.date().isoformat()
            if day_str not in capacity:
                capacity[day_str] = daily_hours
            slot_hours = min(hours_left, capacity[day_str])
            if slot_hours <= 0:
                continue
            schedule.append(
                {
                    "task_id": task.id,
                    "task_title": task.title,
                    "date": day_str,
                    "hours_assigned": round(slot_hours, 2),
                    "priority": task.priority,
                    "deadline": task.deadline.date().isoformat(),
                }
            )
            capacity[day_str] -= slot_hours
            hours_left -= slot_hours
            assigned += slot_hours

        if hours_left > 0.01:
            unscheduled.append(
                {
                    "task_id": task.id,
                    "task_title": task.title,
                    "hours_unscheduled": round(hours_left, 2),
                    "reason": "Insufficient working days before deadline",
                }
            )

    # Sort schedule chronologically then by priority (desc)
    schedule.sort(key=lambda s: (s["date"], -s["priority"]))

    working_days_used = len({s["date"] for s in schedule})

    return {
        "schedule": schedule,
        "unscheduled": unscheduled,
        "total_days_used": working_days_used,
        "summary": {
            "scheduled_count": len(tasks) - len(unscheduled),
            "unscheduled_count": len(unscheduled),
            "total_slots": len(schedule),
        },
    }


def _sort_by_urgency(tasks: List[Task], reference: datetime) -> List[Task]:
    """
    Return tasks sorted by a composite urgency score.

    Score = (days_until_deadline / (estimated_hours + 1)) * (1 / priority)

    Lower score → higher urgency → scheduled first.
    """
    def _urgency(task: Task) -> float:
        days = max(task.days_until_deadline(reference), 0.0)
        # Avoid division by zero; overdue tasks get maximum urgency
        if days == 0:
            return -float("inf")
        return (days / (task.estimated_hours + 1.0)) * (1.0 / task.priority)

    return sorted(tasks, key=_urgency)
