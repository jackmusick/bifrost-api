"""
Scoped Repository
Provides org-scoped queries with automatic GLOBAL fallback
"""

import logging
from typing import TYPE_CHECKING

from .base import BaseRepository

if TYPE_CHECKING:
    from shared.context import ExecutionContext

logger = logging.getLogger(__name__)


class ScopedRepository(BaseRepository):
    """
    Repository with automatic org-scoped + GLOBAL fallback

    Use this for entities that support both:
    - Org-specific instances (stored in org partition)
    - Global instances (stored in GLOBAL partition, visible to all)

    Examples:
    - Forms: Global forms visible to all, org forms only to that org
    - OAuth Connections: Platform OAuth or org-specific OAuth
    - Config: Global defaults, org overrides

    Usage:
        repo = ScopedRepository("Entities", context)
        form = repo.get_with_fallback("form:123")
        # Tries: org_id/form:123, then GLOBAL/form:123
    """

    def __init__(self, table_name: str, context: 'ExecutionContext'):
        """
        Initialize scoped repository

        Args:
            table_name: Name of the Azure Table
            context: RequestContext (required for scoping)
        """
        super().__init__(table_name, context)

        if context is None:
            raise ValueError(
                f"{self.__class__.__name__} requires a ExecutionContext for scoping"
            )

        self.org_id = context.org_id or "GLOBAL"
        self.scope = context.scope  # May be different from org_id for admins

    def get_with_fallback(self, row_key: str) -> dict | None:
        """
        Try org partition first, fallback to GLOBAL if not found

        This implements the org → GLOBAL fallback pattern used throughout
        the codebase for forms, OAuth connections, and config.

        Args:
            row_key: Row key to look up (e.g., "form:123")

        Returns:
            Entity dictionary or None if not found in either partition

        Example:
            # User from org "acme-corp" looking up form "abc-123"
            form = repo.get_with_fallback("form:abc-123")

            # Tries:
            # 1. acme-corp/form:abc-123 (org-specific form)
            # 2. GLOBAL/form:abc-123 (global form)
        """
        # Try org-specific first
        entity = self.get_by_id(self.scope, row_key)

        if entity:
            logger.debug(
                f"Found entity in org partition: {self.scope}/{row_key}"
            )
            return entity

        # Fallback to GLOBAL if not already GLOBAL
        if self.scope != "GLOBAL":
            entity = self.get_by_id("GLOBAL", row_key)

            if entity:
                logger.debug(
                    f"Found entity in GLOBAL partition (fallback): GLOBAL/{row_key}"
                )
                return entity

        logger.debug(
            f"Entity not found in org or GLOBAL: {row_key}"
        )
        return None

    def query_with_fallback(
        self,
        row_key_prefix: str,
        additional_filter: str | None = None,
        select: list[str] | None = None
    ) -> list[dict]:
        """
        Query both org and GLOBAL partitions, merge results (deduplicated)

        This implements the dual-partition query pattern for listing
        entities visible to the user.

        Args:
            row_key_prefix: Row key prefix (e.g., "form:")
            additional_filter: Optional additional OData filter
            select: List of properties to select

        Returns:
            List of entities from both partitions (deduplicated by RowKey)

        Example:
            # List all forms visible to user in org "acme-corp"
            forms = repo.query_with_fallback("form:", additional_filter="IsActive eq true")

            # Returns:
            # - All forms in acme-corp partition
            # - All forms in GLOBAL partition
            # - Deduplicated by RowKey
        """
        results = []
        seen_row_keys = set()

        # Build base filter for row key prefix
        base_filter = (
            f"RowKey ge '{row_key_prefix}' and RowKey lt '{row_key_prefix}~'"
        )

        # Add additional filter if provided
        if additional_filter:
            base_filter = f"{base_filter} and {additional_filter}"

        # Query org partition
        org_filter = f"PartitionKey eq '{self.scope}' and {base_filter}"

        for entity in self.query(org_filter, select=select):
            row_key = entity['RowKey']
            if row_key not in seen_row_keys:
                results.append(entity)
                seen_row_keys.add(row_key)

        # Query GLOBAL partition (if not already GLOBAL)
        if self.scope != "GLOBAL":
            global_filter = f"PartitionKey eq 'GLOBAL' and {base_filter}"

            for entity in self.query(global_filter, select=select):
                row_key = entity['RowKey']
                if row_key not in seen_row_keys:
                    results.append(entity)
                    seen_row_keys.add(row_key)

        logger.debug(
            f"Found {len(results)} entities with fallback: "
            f"{row_key_prefix} (org={self.scope}, deduplicated={len(seen_row_keys)})"
        )

        return results

    def query_org_only(
        self,
        row_key_prefix: str,
        additional_filter: str | None = None,
        select: list[str] | None = None
    ) -> list[dict]:
        """
        Query only the org partition (no GLOBAL fallback)

        Use this when you specifically want org-scoped entities only.

        Args:
            row_key_prefix: Row key prefix
            additional_filter: Optional additional OData filter
            select: List of properties to select

        Returns:
            List of entities from org partition only
        """
        base_filter = (
            f"PartitionKey eq '{self.scope}' and "
            f"RowKey ge '{row_key_prefix}' and RowKey lt '{row_key_prefix}~'"
        )

        if additional_filter:
            base_filter = f"{base_filter} and {additional_filter}"

        return list(self.query(base_filter, select=select))

    def query_global_only(
        self,
        row_key_prefix: str,
        additional_filter: str | None = None,
        select: list[str] | None = None
    ) -> list[dict]:
        """
        Query only the GLOBAL partition

        Use this when you specifically want global entities only.

        Args:
            row_key_prefix: Row key prefix
            additional_filter: Optional additional OData filter
            select: List of properties to select

        Returns:
            List of entities from GLOBAL partition only
        """
        base_filter = (
            f"PartitionKey eq 'GLOBAL' and "
            f"RowKey ge '{row_key_prefix}' and RowKey lt '{row_key_prefix}~'"
        )

        if additional_filter:
            base_filter = f"{base_filter} and {additional_filter}"

        return list(self.query(base_filter, select=select))
