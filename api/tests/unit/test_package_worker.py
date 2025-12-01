"""
Unit tests for package installation worker
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from functions.queue.package_worker import handle_package_install


@pytest.mark.asyncio
async def test_handle_package_install_specific_package(tmp_path):
    """Test installing a specific package"""
    message_data = {
        "job_id": "test-job-123",
        "package": "requests",
        "version": "2.31.0",
        "connection_id": "conn-123",
        "user_id": "user-123",
        "user_email": "test@example.com"
    }

    # Mock WorkspacePackageManager
    with patch('functions.queue.package_worker.WorkspacePackageManager') as MockPkgManager, \
         patch('functions.queue.package_worker.WebPubSubBroadcaster') as MockBroadcaster, \
         patch.dict('os.environ', {'BIFROST_WORKSPACE_LOCATION': str(tmp_path)}):

        mock_pkg_manager = MagicMock()
        mock_pkg_manager.install_package = AsyncMock()
        MockPkgManager.return_value = mock_pkg_manager

        mock_broadcaster = MagicMock()
        mock_broadcaster.enabled = True
        mock_client = MagicMock()
        mock_broadcaster.client = mock_client
        MockBroadcaster.return_value = mock_broadcaster

        # Execute
        await handle_package_install(message_data)

        # Verify install_package was called
        mock_pkg_manager.install_package.assert_called_once()
        call_args = mock_pkg_manager.install_package.call_args
        assert call_args.kwargs['package_name'] == 'requests'
        assert call_args.kwargs['version'] == '2.31.0'
        assert call_args.kwargs['append_to_requirements'] is True
        assert callable(call_args.kwargs['log_callback'])

        # Verify completion message was sent
        assert mock_client.send_to_connection.called
        completion_calls = [
            call for call in mock_client.send_to_connection.call_args_list
            if call.kwargs.get('message', {}).get('type') == 'complete'
        ]
        assert len(completion_calls) == 1
        assert completion_calls[0].kwargs['message']['status'] == 'success'


@pytest.mark.asyncio
async def test_handle_package_install_from_requirements(tmp_path):
    """Test installing from requirements.txt"""
    message_data = {
        "job_id": "test-job-456",
        "package": None,  # No package = install from requirements.txt
        "version": None,
        "connection_id": "conn-456",
        "user_id": "user-456",
        "user_email": "test@example.com"
    }

    with patch('functions.queue.package_worker.WorkspacePackageManager') as MockPkgManager, \
         patch('functions.queue.package_worker.WebPubSubBroadcaster') as MockBroadcaster, \
         patch.dict('os.environ', {'BIFROST_WORKSPACE_LOCATION': str(tmp_path)}):

        mock_pkg_manager = MagicMock()
        mock_pkg_manager.install_requirements_streaming = AsyncMock()
        MockPkgManager.return_value = mock_pkg_manager

        mock_broadcaster = MagicMock()
        mock_broadcaster.enabled = True
        mock_client = MagicMock()
        mock_broadcaster.client = mock_client
        MockBroadcaster.return_value = mock_broadcaster

        # Execute
        await handle_package_install(message_data)

        # Verify install_requirements_streaming was called
        mock_pkg_manager.install_requirements_streaming.assert_called_once()
        call_args = mock_pkg_manager.install_requirements_streaming.call_args
        assert callable(call_args.kwargs['log_callback'])

        # Verify completion message was sent
        assert mock_client.send_to_connection.called


@pytest.mark.asyncio
async def test_handle_package_install_error_handling(tmp_path):
    """Test error handling in package installation"""
    message_data = {
        "job_id": "test-job-789",
        "package": "nonexistent-package",
        "version": None,
        "connection_id": "conn-789",
        "user_id": "user-789",
        "user_email": "test@example.com"
    }

    with patch('functions.queue.package_worker.WorkspacePackageManager') as MockPkgManager, \
         patch('functions.queue.package_worker.WebPubSubBroadcaster') as MockBroadcaster, \
         patch.dict('os.environ', {'BIFROST_WORKSPACE_LOCATION': str(tmp_path)}):

        mock_pkg_manager = MagicMock()
        # Simulate installation failure
        mock_pkg_manager.install_package = AsyncMock(side_effect=Exception("Package not found"))
        MockPkgManager.return_value = mock_pkg_manager

        mock_broadcaster = MagicMock()
        mock_broadcaster.enabled = True
        mock_client = MagicMock()
        mock_broadcaster.client = mock_client
        MockBroadcaster.return_value = mock_broadcaster

        # Execute - should raise to trigger retry/poison queue
        with pytest.raises(Exception, match="Package not found"):
            await handle_package_install(message_data)

        # Verify error completion message was sent
        completion_calls = [
            call for call in mock_client.send_to_connection.call_args_list
            if call.kwargs.get('message', {}).get('type') == 'complete'
        ]
        assert len(completion_calls) == 1
        assert completion_calls[0].kwargs['message']['status'] == 'error'
        assert 'Package not found' in completion_calls[0].kwargs['message']['message']


@pytest.mark.asyncio
async def test_handle_package_install_no_webpubsub(tmp_path):
    """Test package installation without WebPubSub connection"""
    message_data = {
        "job_id": "test-job-999",
        "package": "requests",
        "version": None,
        "connection_id": None,  # No connection ID
        "user_id": "user-999",
        "user_email": "test@example.com"
    }

    with patch('functions.queue.package_worker.WorkspacePackageManager') as MockPkgManager, \
         patch('functions.queue.package_worker.WebPubSubBroadcaster') as MockBroadcaster, \
         patch.dict('os.environ', {'BIFROST_WORKSPACE_LOCATION': str(tmp_path)}):

        mock_pkg_manager = MagicMock()
        mock_pkg_manager.install_package = AsyncMock()
        MockPkgManager.return_value = mock_pkg_manager

        mock_broadcaster = MagicMock()
        mock_broadcaster.enabled = False  # WebPubSub disabled
        mock_broadcaster.client = None
        MockBroadcaster.return_value = mock_broadcaster

        # Execute - should work without WebPubSub
        await handle_package_install(message_data)

        # Verify install_package was called
        mock_pkg_manager.install_package.assert_called_once()
