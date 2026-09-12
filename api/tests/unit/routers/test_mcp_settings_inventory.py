"""Admin settings remain usable when runtime MCP access is restricted."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.routers.mcp import list_mcp_tools
from src.services.mcp_server.tool_access import MCPToolAccessResult


@pytest.mark.asyncio
@pytest.mark.parametrize("is_admin,enabled", [(True, False), (True, True), (False, True), (False, False)])
async def test_settings_inventory_respects_admin_and_runtime_boundaries(is_admin, enabled):
    user = SimpleNamespace(
        roles=[], is_superuser=is_admin, user_id=uuid4(),
        organization_id=None, is_external=False,
    )
    session = AsyncMock()
    with (
        patch("src.routers.mcp.MCPConfigService") as config_cls,
        patch("src.services.mcp_server.tool_access.MCPToolAccessService") as tools_cls,
    ):
        config_cls.return_value.get_config = AsyncMock(
            return_value=SimpleNamespace(enabled=enabled),
        )
        inventory = AsyncMock(return_value=MCPToolAccessResult(tools=[]))
        tools_cls.return_value.get_accessible_tools = inventory
        if not is_admin and not enabled:
            with pytest.raises(HTTPException) as raised:
                await list_mcp_tools(user, session)
            assert raised.value.status_code == 403
            inventory.assert_not_awaited()
        else:
            result = await list_mcp_tools(user, session)
            assert result.tools == []
            assert inventory.await_args.kwargs["for_configuration"] is is_admin
