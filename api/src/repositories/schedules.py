"""
Schedule Repository

PostgreSQL-based repository for scheduled workflows (CRON schedules).
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm import Schedule
from src.repositories.org_scoped import OrgScopedRepository


class ScheduleRepository(OrgScopedRepository[Schedule]):
    """
    Repository for scheduled workflows.

    Stores CRON schedule metadata with:
    - id: UUID primary key
    - organization_id: Organization scope (nullable for global schedules)
    - workflow_name: Name of the workflow to schedule (String(255))
    - cron_expression: CRON expression string (String(100))
    - parameters: Optional workflow parameters (JSONB)
    - enabled: Whether schedule is active (default True)
    - created_at: Schedule creation timestamp
    - updated_at: Last modification timestamp
    - created_by: User who created the schedule (nullable FK to users)
    - last_run_at: Timestamp of last execution (nullable)

    Uses CASCADE scoping pattern: org-specific + global (NULL) schedules visible.
    """

    model = Schedule

    async def create_schedule(
        self,
        workflow_name: str,
        cron_expression: str,
        parameters: dict[str, Any] | None = None,
        enabled: bool = True,
        created_by: UUID | None = None,
    ) -> Schedule:
        """
        Create a new schedule.

        Args:
            workflow_name: Name of the workflow
            cron_expression: CRON expression for scheduling
            parameters: Optional workflow parameters as dict
            enabled: Whether schedule is enabled (default True)
            created_by: User ID who created the schedule

        Returns:
            Created schedule
        """
        schedule = Schedule(
            organization_id=self.org_id,
            workflow_name=workflow_name,
            cron_expression=cron_expression,
            parameters=parameters,
            enabled=enabled,
            created_by=created_by,
        )
        self.session.add(schedule)
        await self.session.flush()
        await self.session.refresh(schedule)
        return schedule

    async def get_schedule(self, schedule_id: UUID) -> Schedule | None:
        """
        Get a single schedule by ID (with CASCADE scoping).

        Uses CASCADE filter to include org-specific + global schedules.

        Args:
            schedule_id: Schedule UUID

        Returns:
            Schedule or None if not found or not accessible
        """
        query = select(Schedule).where(Schedule.id == schedule_id)
        query = self.filter_cascade(query)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_schedule_strict(self, schedule_id: UUID) -> Schedule | None:
        """
        Get a single schedule by ID (organization-specific only).

        Uses STRICT filter to only include org-specific schedules (no global).

        Args:
            schedule_id: Schedule UUID

        Returns:
            Schedule or None if not found or belongs to different org
        """
        query = select(Schedule).where(Schedule.id == schedule_id)
        query = self.filter_strict(query)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_schedules(
        self,
        workflow_name: str | None = None,
        enabled_only: bool = False,
    ) -> list[Schedule]:
        """
        List schedules with optional filtering.

        Uses CASCADE scoping (org-specific + global).

        Args:
            workflow_name: Optional filter by workflow name
            enabled_only: If True, only return enabled schedules

        Returns:
            List of schedules
        """
        query = select(Schedule)
        query = self.filter_cascade(query)

        if workflow_name:
            query = query.where(Schedule.workflow_name == workflow_name)

        if enabled_only:
            query = query.where(Schedule.enabled.is_(True))

        query = query.order_by(Schedule.workflow_name)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_schedule(
        self,
        schedule_id: UUID,
        cron_expression: str | None = None,
        parameters: dict[str, Any] | None = None,
        enabled: bool | None = None,
    ) -> Schedule | None:
        """
        Update a schedule.

        Args:
            schedule_id: Schedule UUID
            cron_expression: New CRON expression (if provided)
            parameters: New parameters dict (if provided)
            enabled: New enabled status (if provided)

        Returns:
            Updated schedule or None if not found
        """
        schedule = await self.get_schedule_strict(schedule_id)
        if not schedule:
            return None

        if cron_expression is not None:
            schedule.cron_expression = cron_expression
        if parameters is not None:
            schedule.parameters = parameters
        if enabled is not None:
            schedule.enabled = enabled

        schedule.updated_at = datetime.utcnow()

        self.session.add(schedule)
        await self.session.flush()
        await self.session.refresh(schedule)
        return schedule

    async def delete_schedule(self, schedule_id: UUID) -> bool:
        """
        Delete a schedule.

        Args:
            schedule_id: Schedule UUID

        Returns:
            True if deleted, False if not found
        """
        schedule = await self.get_schedule_strict(schedule_id)
        if not schedule:
            return False

        self.session.delete(schedule)
        await self.session.flush()
        return True

    async def get_due_schedules(self) -> list[Schedule]:
        """
        Get all enabled schedules that are due to run.

        Used by scheduler worker to find schedules for processing.
        Returns only enabled schedules with CASCADE scoping.

        Returns:
            List of enabled schedules accessible to this org
        """
        query = select(Schedule)
        query = self.filter_cascade(query)
        query = query.where(Schedule.enabled.is_(True))
        query = query.order_by(Schedule.workflow_name)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_last_run(self, schedule_id: UUID, timestamp: datetime | None = None) -> None:
        """
        Update the last_run_at timestamp for a schedule.

        Args:
            schedule_id: Schedule UUID
            timestamp: Timestamp to set (defaults to now)
        """
        schedule = await self.get_schedule_strict(schedule_id)
        if not schedule:
            return

        schedule.last_run_at = timestamp or datetime.utcnow()
        self.session.add(schedule)
        await self.session.flush()

    async def count_schedules(self, enabled_only: bool = False) -> int:
        """
        Count schedules with optional filtering.

        Args:
            enabled_only: If True, only count enabled schedules

        Returns:
            Total number of schedules
        """
        query = select(func.count(Schedule.id))
        query = self.filter_cascade(query)

        if enabled_only:
            query = query.where(Schedule.enabled.is_(True))

        result = await self.session.execute(query)
        return result.scalar_one()
