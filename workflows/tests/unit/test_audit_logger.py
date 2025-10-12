"""
Unit Tests: Audit Logger (T062)

Tests the AuditLogger class in isolation:
- Entity creation with correct partition/row keys
- Date-based partitioning
- Reverse timestamp sorting
- Event-specific data formatting
- Connection string handling
- Singleton pattern
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import uuid


class TestAuditLogger:
    """Unit tests for AuditLogger"""

    @pytest.fixture
    def mock_table_client(self):
        """Create mock table client"""
        client = AsyncMock()
        client.create_entity = AsyncMock()
        return client

    @pytest.fixture
    def audit_logger(self, mock_table_client):
        """Create AuditLogger with mocked table client"""
        from engine.shared.audit import AuditLogger

        logger = AuditLogger(connection_string="UseDevelopmentStorage=true")
        logger._table_client = mock_table_client
        logger._enabled = True

        return logger

    def test_audit_logger_initialization_with_connection_string(self):
        """Test AuditLogger initializes with provided connection string"""
        from engine.shared.audit import AuditLogger

        logger = AuditLogger(connection_string="test_connection_string")

        assert logger.connection_string == "test_connection_string"
        assert logger._enabled is True

    def test_audit_logger_initialization_from_env(self):
        """Test AuditLogger reads connection string from environment"""
        from engine.shared.audit import AuditLogger

        with patch.dict('os.environ', {'TABLE_STORAGE_CONNECTION_STRING': 'env_connection'}):
            logger = AuditLogger()

            assert logger.connection_string == 'env_connection'
            assert logger._enabled is True

    def test_audit_logger_disabled_when_no_connection_string(self):
        """Test AuditLogger is disabled when no connection string available"""
        from engine.shared.audit import AuditLogger

        with patch.dict('os.environ', {}, clear=True):
            with patch('engine.shared.audit.logger') as mock_logger:
                logger = AuditLogger()

                assert logger._enabled is False
                mock_logger.warning.assert_called_once()

    def test_create_entity_partition_key_format(self, audit_logger):
        """Test that partition key is date in YYYY-MM-DD format"""
        timestamp = datetime(2025, 1, 15, 10, 30, 45, tzinfo=timezone.utc)

        entity = audit_logger._create_entity(
            event_type='test_event',
            timestamp=timestamp,
            data={'field': 'value'}
        )

        assert entity['PartitionKey'] == '2025-01-15'

    def test_create_entity_row_key_format(self, audit_logger):
        """Test that row key is reverse_timestamp_uuid format"""
        timestamp = datetime(2025, 1, 15, 10, 30, 45, tzinfo=timezone.utc)

        entity = audit_logger._create_entity(
            event_type='test_event',
            timestamp=timestamp,
            data={}
        )

        # Row key should be: reverse_ticks_uuid
        assert '_' in entity['RowKey']
        parts = entity['RowKey'].split('_')
        assert len(parts) == 2
        assert parts[0].isdigit()  # Reverse ticks
        assert len(parts[1]) == 32  # UUID hex (no hyphens)

    def test_create_entity_reverse_timestamp_sorting(self, audit_logger):
        """Test that newer events have smaller row keys (sort first)"""
        earlier_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        later_time = datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc)

        entity1 = audit_logger._create_entity('test', earlier_time, {})
        entity2 = audit_logger._create_entity('test', later_time, {})

        # Extract reverse ticks from row keys
        ticks1 = int(entity1['RowKey'].split('_')[0])
        ticks2 = int(entity2['RowKey'].split('_')[0])

        # Later event should have smaller reverse ticks (sorts first)
        assert ticks2 < ticks1

    def test_create_entity_includes_event_type(self, audit_logger):
        """Test that entity includes EventType field"""
        entity = audit_logger._create_entity(
            event_type='function_key_access',
            timestamp=datetime.now(timezone.utc),
            data={}
        )

        assert entity['EventType'] == 'function_key_access'

    def test_create_entity_includes_timestamp_iso(self, audit_logger):
        """Test that entity includes ISO format timestamp"""
        timestamp = datetime(2025, 1, 15, 10, 30, 45, tzinfo=timezone.utc)

        entity = audit_logger._create_entity(
            event_type='test',
            timestamp=timestamp,
            data={}
        )

        assert entity['Timestamp'] == '2025-01-15T10:30:45+00:00'

    def test_create_entity_merges_event_data(self, audit_logger):
        """Test that entity includes event-specific data fields"""
        data = {
            'KeyId': 'key123',
            'OrgId': 'org-456',
            'Endpoint': '/api/workflows',
            'StatusCode': 200
        }

        entity = audit_logger._create_entity(
            event_type='function_key_access',
            timestamp=datetime.now(timezone.utc),
            data=data
        )

        assert entity['KeyId'] == 'key123'
        assert entity['OrgId'] == 'org-456'
        assert entity['Endpoint'] == '/api/workflows'
        assert entity['StatusCode'] == 200

    @pytest.mark.asyncio
    async def test_log_function_key_access_creates_entity(self, audit_logger, mock_table_client):
        """Test log_function_key_access creates correct entity"""
        await audit_logger.log_function_key_access(
            key_id='key_123',
            key_name='admin',
            org_id='org-456',
            endpoint='/api/workflows',
            method='POST',
            remote_addr='192.168.1.1',
            user_agent='curl/7.64',
            status_code=200,
            details={'extra': 'info'}
        )

        # Verify entity was created
        mock_table_client.create_entity.assert_called_once()

        # Check entity structure
        entity = mock_table_client.create_entity.call_args[0][0]
        assert entity['EventType'] == 'function_key_access'
        assert entity['KeyId'] == 'key_123'
        assert entity['KeyName'] == 'admin'
        assert entity['OrgId'] == 'org-456'
        assert entity['Endpoint'] == '/api/workflows'
        assert entity['Method'] == 'POST'
        assert entity['RemoteAddr'] == '192.168.1.1'
        assert entity['UserAgent'] == 'curl/7.64'
        assert entity['StatusCode'] == 200

    @pytest.mark.asyncio
    async def test_log_cross_org_access_creates_entity(self, audit_logger, mock_table_client):
        """Test log_cross_org_access creates correct entity"""
        await audit_logger.log_cross_org_access(
            user_id='user-123',
            target_org_id='org-789',
            endpoint='/api/workflows',
            method='GET',
            remote_addr='192.168.1.2',
            status_code=200,
            details={'reason': 'Support ticket #1234'}
        )

        mock_table_client.create_entity.assert_called_once()

        entity = mock_table_client.create_entity.call_args[0][0]
        assert entity['EventType'] == 'cross_org_access'
        assert entity['UserId'] == 'user-123'
        assert entity['OrgId'] == 'org-789'

    @pytest.mark.asyncio
    async def test_log_import_violation_attempt_creates_entity(self, audit_logger, mock_table_client):
        """Test log_import_violation_attempt creates correct entity"""
        await audit_logger.log_import_violation_attempt(
            blocked_module='engine.shared.storage',
            workspace_file='/workspace/my_workflow.py',
            stack_trace=['file.py:10', 'other.py:20']
        )

        mock_table_client.create_entity.assert_called_once()

        entity = mock_table_client.create_entity.call_args[0][0]
        assert entity['EventType'] == 'engine_violation_attempt'
        assert entity['BlockedModule'] == 'engine.shared.storage'
        assert entity['WorkspaceFile'] == '/workspace/my_workflow.py'

    @pytest.mark.asyncio
    async def test_log_event_disabled_returns_early(self, audit_logger):
        """Test that logging is skipped when disabled"""
        audit_logger._enabled = False

        await audit_logger._log_event('test_event', {})

        # Table client should not be called
        audit_logger._table_client.create_entity.assert_not_called()

    @pytest.mark.asyncio
    async def test_log_event_handles_errors_gracefully(self, audit_logger, mock_table_client):
        """Test that logging errors don't crash the application"""
        # Make create_entity raise exception
        mock_table_client.create_entity.side_effect = Exception("Table error")

        # Should not raise exception
        with patch('engine.shared.audit.logger') as mock_logger:
            await audit_logger._log_event('test_event', {})

            # Should log error
            mock_logger.error.assert_called()

    def test_get_table_client_lazy_initialization(self):
        """Test that table client is lazy-loaded"""
        from engine.shared.audit import AuditLogger

        logger = AuditLogger(connection_string="UseDevelopmentStorage=true")

        # Table client should be None initially
        assert logger._table_client is None

        # First call should create client
        with patch('engine.shared.audit.TableServiceClient') as mock_service:
            mock_service.from_connection_string.return_value.get_table_client.return_value = Mock()

            client = logger._get_table_client()

            assert client is not None
            assert logger._table_client is not None

    def test_get_table_client_returns_none_when_disabled(self):
        """Test that disabled logger returns None for table client"""
        from engine.shared.audit import AuditLogger

        with patch.dict('os.environ', {}, clear=True):
            logger = AuditLogger()

            client = logger._get_table_client()
            assert client is None

    def test_get_table_client_handles_errors(self):
        """Test that table client creation errors disable logger"""
        from engine.shared.audit import AuditLogger

        logger = AuditLogger(connection_string="UseDevelopmentStorage=true")

        with patch('engine.shared.audit.TableServiceClient') as mock_service:
            mock_service.from_connection_string.side_effect = Exception("Connection error")

            with patch('engine.shared.audit.logger') as mock_logger:
                client = logger._get_table_client()

                assert client is None
                assert logger._enabled is False
                mock_logger.error.assert_called()

    def test_singleton_get_audit_logger(self):
        """Test that get_audit_logger returns singleton instance"""
        from engine.shared.audit import get_audit_logger, _audit_logger_instance
        import engine.shared.audit as audit_module

        # Clear singleton
        audit_module._audit_logger_instance = None

        logger1 = get_audit_logger()
        logger2 = get_audit_logger()

        # Should be same instance
        assert logger1 is logger2

    @pytest.mark.asyncio
    async def test_details_serialized_to_json(self, audit_logger, mock_table_client):
        """Test that details dict is serialized to JSON string"""
        details = {'key1': 'value1', 'key2': 123, 'key3': True}

        await audit_logger.log_function_key_access(
            key_id='key', key_name='name', org_id='org', endpoint='/api',
            method='POST', remote_addr='127.0.0.1', user_agent='test',
            status_code=200, details=details
        )

        entity = mock_table_client.create_entity.call_args[0][0]

        # Details should be JSON string
        import json
        assert isinstance(entity['Details'], str)
        parsed = json.loads(entity['Details'])
        assert parsed == details

    @pytest.mark.asyncio
    async def test_none_details_handled(self, audit_logger, mock_table_client):
        """Test that None details is handled correctly"""
        await audit_logger.log_function_key_access(
            key_id='key', key_name='name', org_id='org', endpoint='/api',
            method='POST', remote_addr='127.0.0.1', user_agent='test',
            status_code=200, details=None
        )

        entity = mock_table_client.create_entity.call_args[0][0]

        # Details should be None (not JSON string)
        assert entity['Details'] is None

    def test_partition_key_consistency_same_day(self, audit_logger):
        """Test that events on same day share partition key"""
        time1 = datetime(2025, 1, 15, 8, 0, 0, tzinfo=timezone.utc)
        time2 = datetime(2025, 1, 15, 20, 0, 0, tzinfo=timezone.utc)

        entity1 = audit_logger._create_entity('test', time1, {})
        entity2 = audit_logger._create_entity('test', time2, {})

        assert entity1['PartitionKey'] == entity2['PartitionKey']

    def test_partition_key_different_days(self, audit_logger):
        """Test that events on different days have different partition keys"""
        time1 = datetime(2025, 1, 15, 23, 59, 59, tzinfo=timezone.utc)
        time2 = datetime(2025, 1, 16, 0, 0, 1, tzinfo=timezone.utc)

        entity1 = audit_logger._create_entity('test', time1, {})
        entity2 = audit_logger._create_entity('test', time2, {})

        assert entity1['PartitionKey'] != entity2['PartitionKey']
        assert entity1['PartitionKey'] == '2025-01-15'
        assert entity2['PartitionKey'] == '2025-01-16'
