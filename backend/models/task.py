"""Task data model for the deadline conflict resolver."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Task:
    """Represents a task with deadline and workload information."""

    id: str
    title: str
    deadline: datetime
    estimated_hours: float
    priority: int  # 1 (low) to 5 (high)
    description: str = ""
    start_date: Optional[datetime] = None
    dependencies: list = field(default_factory=list)

    def days_until_deadline(self, from_date: Optional[datetime] = None) -> float:
        """Return the number of days until the deadline from now or a given date."""
        reference = from_date or datetime.now()
        deadline = self.deadline
        # Normalise both to naive UTC to avoid offset-aware vs offset-naive errors
        if deadline.tzinfo is not None:
            deadline = deadline.astimezone(timezone.utc).replace(tzinfo=None)
        if reference.tzinfo is not None:
            reference = reference.astimezone(timezone.utc).replace(tzinfo=None)
        delta = deadline - reference
        return delta.total_seconds() / 86400

    def is_overdue(self, from_date: Optional[datetime] = None) -> bool:
        """Return True if the task deadline has already passed."""
        return self.days_until_deadline(from_date) < 0

    def hours_per_day_required(self, from_date: Optional[datetime] = None) -> float:
        """Return the average hours per day needed to complete the task on time."""
        days = self.days_until_deadline(from_date)
        if days <= 0:
            return float("inf")
        return self.estimated_hours / days

    def to_dict(self) -> dict:
        """Serialize the task to a dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "deadline": self.deadline.isoformat(),
            "estimated_hours": self.estimated_hours,
            "priority": self.priority,
            "description": self.description,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "dependencies": self.dependencies,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Deserialize a task from a dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            deadline=datetime.fromisoformat(data["deadline"]),
            estimated_hours=float(data["estimated_hours"]),
            priority=int(data["priority"]),
            description=data.get("description", ""),
            start_date=(
                datetime.fromisoformat(data["start_date"])
                if data.get("start_date")
                else None
            ),
            dependencies=data.get("dependencies", []),
        )
