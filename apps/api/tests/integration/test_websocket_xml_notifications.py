"""
Integration tests for WebSocket progress notifications during XML generation
"""
import pytest
import asyncio
import json
import io
import csv
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import UploadFile, WebSocket
from sqlalchemy.orm import Session

from src.services.file_processing import FileProcessingService
from src.models.user import User, SubscriptionTier
from src.models.processing_job import ProcessingJob, ProcessingStatus
from src.models.product_match import ProductMatch
from src.core.openai_config import HSCodeResult, HSCodeMatchResult
from src.api.v1.ws import manager as websocket_manager, ConnectionManager


@pytest.fixture
def test_user():
    """Create test user"""
    return User(
        id=1,
        email="test@example.com",
        username="testuser",
        subscription_tier=SubscriptionTier.BASIC,
        credits_remaining=100,
        credits_used_this_month=0
    )


@pytest.fixture
def sample_csv_content():
    """Create sample CSV content for testing"""
    csv_content = io.StringIO()
    writer = csv.writer(csv_content)
    
    # Write headers
    writer.writerow(['Product Description', 'Quantity', 'Unit', 'Value', 'Origin Country', 'Unit Price'])
    
    # Write sample data
    writer.writerow(['Apple iPhone 14', '10', 'pcs', '12000.00', 'China', '1200.00'])
    writer.writerow(['Samsung Galaxy S23', '5', 'pcs', '4000.00', 'South Korea', '800.00'])
    writer.writerow(['Dell Laptop XPS 13', '3', 'pcs', '3600.00', 'Taiwan', '1200.00'])
    
    return csv_content.getvalue().encode('utf-8')


@pytest.fixture
def mock_upload_file(sample_csv_content):
    """Create mock UploadFile for testing"""
    file = MagicMock(spec=UploadFile)
    file.filename = "test_products.csv"
    file.size = len(sample_csv_content)
    file.content_type = "text/csv"
    file.read = AsyncMock(return_value=sample_csv_content)
    file.seek = AsyncMock()
    return file


@pytest.fixture
def mock_hs_matching_results():
    """Mock HS code matching results"""
    return [
        HSCodeMatchResult(
            primary_match=HSCodeResult(
                hs_code="8517.12.00",
                code_description="Telephones for cellular networks",
                confidence=0.95,
                chapter="85",
                section="XVI",
                reasoning="iPhone is clearly a cellular telephone"
            ),
            alternative_matches=[],
            processing_time_ms=1200.0,
            query="Apple iPhone 14"
        ),
        HSCodeMatchResult(
            primary_match=HSCodeResult(
                hs_code="8517.12.00",
                code_description="Telephones for cellular networks",
                confidence=0.92,
                chapter="85",
                section="XVI",
                reasoning="Samsung Galaxy is a cellular telephone"
            ),
            alternative_matches=[],
            processing_time_ms=1100.0,
            query="Samsung Galaxy S23"
        ),
        HSCodeMatchResult(
            primary_match=HSCodeResult(
                hs_code="8471.30.01",
                code_description="Portable digital automatic data processing machines",
                confidence=0.88,
                chapter="84",
                section="XVI",
                reasoning="Dell XPS 13 is a portable laptop computer"
            ),
            alternative_matches=[],
            processing_time_ms=1300.0,
            query="Dell Laptop XPS 13"
        )
    ]


class MockWebSocket:
    """Mock WebSocket for testing"""
    
    def __init__(self):
        self.messages = []
        self.closed = False
        
    async def accept(self):
        pass
        
    async def send_text(self, message: str):
        if not self.closed:
            self.messages.append(json.loads(message))
            
    async def receive_text(self):
        return '{"type": "ping"}'
        
    async def close(self, code: int = 1000, reason: str = ""):
        self.closed = True


class TestWebSocketXMLNotifications:
    """Integration tests for WebSocket progress notifications during XML generation"""

    @pytest.mark.asyncio
    async def test_websocket_connection_and_authentication(self):
        """Test WebSocket connection establishment and authentication"""
        
        # Create mock WebSocket
        mock_websocket = MockWebSocket()
        
        # Mock authentication
        mock_user = User(id=1, email="test@example.com", username="testuser")
        
        with patch('src.api.v1.ws.get_current_user_ws') as mock_auth:
            mock_auth.return_value = mock_user
            
            # Test connection manager
            manager = ConnectionManager()
            
            # Connect WebSocket
            await manager.connect(mock_websocket, "1")
            
            # Verify connection was established
            assert "1" in manager.active_connections
            assert mock_websocket in manager.active_connections["1"]
            
            # Test sending message
            test_message = {"type": "test", "data": "Hello WebSocket"}
            await manager.send_personal_message(test_message, "1")
            
            # Verify message was sent
            assert len(mock_websocket.messages) == 1
            assert mock_websocket.messages[0]["type"] == "test"
            assert mock_websocket.messages[0]["data"] == "Hello WebSocket"

    @pytest.mark.asyncio
    async def test_processing_progress_notifications(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test progress notifications during file processing workflow"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Create mock WebSocket and connect
        mock_websocket = MockWebSocket()
        manager = ConnectionManager()
        await manager.connect(mock_websocket, "1")
        
        # Initialize services
        file_service = FileProcessingService(db_session)
        
        # Mock S3 upload
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock) as mock_s3_upload:
            mock_s3_upload.return_value = "s3://test-bucket/uploads/1/test_products.csv"
            
            # Mock XML storage
            with patch('src.services.xml_storage.xml_storage_service.store_xml_file', new_callable=AsyncMock) as mock_xml_store:
                mock_xml_store.return_value = {
                    'file_path': 's3://test-bucket/xml/job_1_export.xml',
                    'download_url': 'https://presigned-download-url.com',
                    'file_size': 2048,
                    'expires_at': '2025-01-23T12:00:00Z'
                }
                
                # Mock HS matching service
                with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                    mock_hs_service.match_batch_products = AsyncMock(return_value=mock_hs_matching_results)
                    mock_hs_service.should_require_manual_review.return_value = False
                    
                    # Patch the global websocket manager to use our test manager
                    with patch('src.services.file_processing.websocket_manager', manager):
                        
                        # Execute workflow
                        result = await file_service.process_file_with_hs_matching(
                            file=mock_upload_file,
                            user=test_user,
                            country_schema="turkmenistan"
                        )
                        
                        # Verify processing succeeded
                        assert result["success"] is True
                        
                        # Verify progress notifications were sent
                        messages = mock_websocket.messages
                        assert len(messages) >= 8  # Should have multiple progress updates
                        
                        # Verify message structure
                        for message in messages:
                            assert "type" in message
                            assert message["type"] == "processing_update"
                            assert "job_id" in message
                            assert "status" in message
                            assert "progress" in message
                            assert "timestamp" in message
                            
                        # Verify progress sequence
                        progress_values = [msg["progress"] for msg in messages]
                        assert 0 in progress_values  # Started
                        assert 100 in progress_values  # Completed
                        
                        # Verify key milestones
                        message_texts = [msg.get("message", "") for msg in messages]
                        assert any("File uploaded successfully" in text for text in message_texts)
                        assert any("HS code matching completed" in text for text in message_texts)
                        assert any("XML generation started" in text for text in message_texts)
                        assert any("XML generation completed" in text for text in message_texts)

    @pytest.mark.asyncio
    async def test_xml_generation_progress_notifications(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test specific XML generation progress notifications"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Create mock WebSocket and connect
        mock_websocket = MockWebSocket()
        manager = ConnectionManager()
        await manager.connect(mock_websocket, "1")
        
        # Initialize services
        file_service = FileProcessingService(db_session)
        
        # Mock S3 upload
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock):
            
            # Mock XML storage with delay to simulate processing
            async def delayed_xml_storage(*args, **kwargs):
                # Send intermediate progress notification
                await manager.send_processing_update(
                    job_id="1",
                    user_id="1",
                    status="generating_xml",
                    progress=75,
                    message="XML template processing...",
                    data={"stage": "template_processing"}
                )
                await asyncio.sleep(0.1)  # Simulate processing time
                return {
                    'file_path': 's3://test-bucket/xml/job_1_export.xml',
                    'download_url': 'https://presigned-download-url.com',
                    'file_size': 2048,
                    'expires_at': '2025-01-23T12:00:00Z'
                }
            
            with patch('src.services.xml_storage.xml_storage_service.store_xml_file', side_effect=delayed_xml_storage):
                
                # Mock HS matching service
                with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                    mock_hs_service.match_batch_products = AsyncMock(return_value=mock_hs_matching_results)
                    mock_hs_service.should_require_manual_review.return_value = False
                    
                    # Patch the global websocket manager
                    with patch('src.services.file_processing.websocket_manager', manager):
                        
                        # Execute workflow
                        result = await file_service.process_file_with_hs_matching(
                            file=mock_upload_file,
                            user=test_user,
                            country_schema="turkmenistan"
                        )
                        
                        # Verify processing succeeded
                        assert result["success"] is True
                        
                        # Find XML-related notifications
                        xml_messages = [
                            msg for msg in mock_websocket.messages
                            if "xml" in msg.get("message", "").lower() or
                            msg.get("data", {}).get("stage") == "template_processing"
                        ]
                        
                        # Verify XML-specific progress notifications
                        assert len(xml_messages) >= 2  # At least start and completion
                        
                        # Verify XML generation stages
                        stages = [msg.get("data", {}).get("stage") for msg in xml_messages]
                        messages = [msg.get("message", "") for msg in xml_messages]
                        
                        assert any("template_processing" in str(stage) for stage in stages)
                        assert any("XML generation" in text for text in messages)

    @pytest.mark.asyncio
    async def test_websocket_error_notifications(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test error notifications via WebSocket during XML generation"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Create mock WebSocket and connect
        mock_websocket = MockWebSocket()
        manager = ConnectionManager()
        await manager.connect(mock_websocket, "1")
        
        # Initialize services
        file_service = FileProcessingService(db_session)
        
        # Mock S3 upload
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock):
            
            # Mock XML generation to fail
            with patch('src.services.xml_generation.xml_generation_service.generate_xml', new_callable=AsyncMock) as mock_xml_gen:
                mock_xml_gen.side_effect = Exception("XML generation service unavailable")
                
                # Mock HS matching service
                with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                    mock_hs_service.match_batch_products = AsyncMock(return_value=mock_hs_matching_results)
                    mock_hs_service.should_require_manual_review.return_value = False
                    
                    # Patch the global websocket manager
                    with patch('src.services.file_processing.websocket_manager', manager):
                        
                        # Execute workflow
                        result = await file_service.process_file_with_hs_matching(
                            file=mock_upload_file,
                            user=test_user,
                            country_schema="turkmenistan"
                        )
                        
                        # Verify partial success (HS matching succeeded)
                        assert result["success"] is True
                        
                        # Find error notifications
                        error_messages = [
                            msg for msg in mock_websocket.messages
                            if msg.get("status") == "error" or
                            "error" in msg.get("message", "").lower() or
                            "failed" in msg.get("message", "").lower()
                        ]
                        
                        # Verify error notifications were sent
                        assert len(error_messages) >= 1
                        
                        # Verify error message content
                        error_message = error_messages[0]
                        assert "XML generation failed" in error_message.get("message", "")
                        assert error_message.get("data", {}).get("error") is not None

    @pytest.mark.asyncio
    async def test_multiple_user_websocket_isolation(self):
        """Test WebSocket message isolation between different users"""
        
        # Create mock WebSockets for different users
        websocket_user1 = MockWebSocket()
        websocket_user2 = MockWebSocket()
        
        # Create connection manager
        manager = ConnectionManager()
        
        # Connect both users
        await manager.connect(websocket_user1, "1")
        await manager.connect(websocket_user2, "2")
        
        # Send message to user 1 only
        await manager.send_processing_update(
            job_id="job_1",
            user_id="1",
            status="processing",
            progress=50,
            message="Processing user 1 file...",
            data={"user": "user1"}
        )
        
        # Send message to user 2 only
        await manager.send_processing_update(
            job_id="job_2",
            user_id="2",
            status="processing",
            progress=25,
            message="Processing user 2 file...",
            data={"user": "user2"}
        )
        
        # Verify message isolation
        assert len(websocket_user1.messages) == 1
        assert len(websocket_user2.messages) == 1
        
        # Verify correct messages were received
        user1_message = websocket_user1.messages[0]
        user2_message = websocket_user2.messages[0]
        
        assert user1_message["job_id"] == "job_1"
        assert user1_message["progress"] == 50
        assert user1_message["data"]["user"] == "user1"
        
        assert user2_message["job_id"] == "job_2"
        assert user2_message["progress"] == 25
        assert user2_message["data"]["user"] == "user2"

    @pytest.mark.asyncio
    async def test_websocket_connection_cleanup(self):
        """Test WebSocket connection cleanup on disconnect"""
        
        # Create mock WebSocket
        mock_websocket = MockWebSocket()
        
        # Create connection manager
        manager = ConnectionManager()
        
        # Connect WebSocket
        await manager.connect(mock_websocket, "1")
        
        # Verify connection exists
        assert "1" in manager.active_connections
        assert mock_websocket in manager.active_connections["1"]
        
        # Disconnect WebSocket
        manager.disconnect(mock_websocket, "1")
        
        # Verify connection was cleaned up
        assert "1" not in manager.active_connections

    @pytest.mark.asyncio
    async def test_websocket_message_ordering(
        self,
        db_session: Session,
        test_user: User,
        mock_upload_file: UploadFile,
        mock_hs_matching_results: list
    ):
        """Test that WebSocket messages are sent in correct order"""
        
        # Add user to database
        db_session.add(test_user)
        db_session.commit()
        
        # Create mock WebSocket with timestamp tracking
        mock_websocket = MockWebSocket()
        manager = ConnectionManager()
        await manager.connect(mock_websocket, "1")
        
        # Initialize services
        file_service = FileProcessingService(db_session)
        
        # Mock S3 upload
        with patch.object(file_service, 'upload_file_to_s3', new_callable=AsyncMock):
            
            # Mock XML storage
            with patch('src.services.xml_storage.xml_storage_service.store_xml_file', new_callable=AsyncMock) as mock_xml_store:
                mock_xml_store.return_value = {
                    'file_path': 's3://test-bucket/xml/job_1_export.xml',
                    'download_url': 'https://presigned-download-url.com',
                    'file_size': 2048,
                    'expires_at': '2025-01-23T12:00:00Z'
                }
                
                # Mock HS matching service
                with patch('src.services.file_processing.hs_matching_service') as mock_hs_service:
                    mock_hs_service.match_batch_products = AsyncMock(return_value=mock_hs_matching_results)
                    mock_hs_service.should_require_manual_review.return_value = False
                    
                    # Patch the global websocket manager
                    with patch('src.services.file_processing.websocket_manager', manager):
                        
                        # Execute workflow
                        result = await file_service.process_file_with_hs_matching(
                            file=mock_upload_file,
                            user=test_user,
                            country_schema="turkmenistan"
                        )
                        
                        # Verify processing succeeded
                        assert result["success"] is True
                        
                        # Extract progress values and timestamps
                        messages = mock_websocket.messages
                        progress_sequence = [
                            (msg["progress"], msg["timestamp"])
                            for msg in messages
                            if "progress" in msg
                        ]
                        
                        # Sort by timestamp
                        progress_sequence.sort(key=lambda x: x[1])
                        
                        # Verify progress is generally increasing
                        progress_values = [p[0] for p in progress_sequence]
                        
                        # Should start at 0 and end at 100
                        assert progress_values[0] == 0
                        assert progress_values[-1] == 100
                        
                        # Should have intermediate values
                        assert any(0 < p < 100 for p in progress_values)

    @pytest.mark.asyncio
    async def test_websocket_large_message_handling(
        self,
        db_session: Session,
        test_user: User
    ):
        """Test WebSocket handling of large messages and data"""
        
        # Create mock WebSocket
        mock_websocket = MockWebSocket()
        manager = ConnectionManager()
        await manager.connect(mock_websocket, "1")
        
        # Create large data payload
        large_data = {
            "products": [
                {
                    "id": i,
                    "description": f"Product {i} with very long description " * 10,
                    "hs_code": f"1234.56.{i:02d}",
                    "details": "x" * 1000  # Large string
                }
                for i in range(100)  # 100 products with large data
            ],
            "metadata": {
                "processing_details": "x" * 5000,  # Large metadata
                "statistics": {"stat_" + str(i): i * 100 for i in range(1000)}  # Large stats
            }
        }
        
        # Send large message
        await manager.send_processing_update(
            job_id="job_1",
            user_id="1",
            status="processing",
            progress=50,
            message="Processing large dataset...",
            data=large_data
        )
        
        # Verify message was sent successfully
        assert len(mock_websocket.messages) == 1
        
        # Verify message structure is intact
        message = mock_websocket.messages[0]
        assert message["type"] == "processing_update"
        assert message["job_id"] == "job_1"
        assert message["progress"] == 50
        assert len(message["data"]["products"]) == 100
        assert len(message["data"]["metadata"]["statistics"]) == 1000

    @pytest.mark.asyncio
    async def test_websocket_connection_recovery(self):
        """Test WebSocket connection recovery after failure"""
        
        # Create mock WebSocket that fails
        class FailingWebSocket(MockWebSocket):
            def __init__(self):
                super().__init__()
                self.fail_count = 0
                
            async def send_text(self, message: str):
                self.fail_count += 1
                if self.fail_count <= 2:  # Fail first 2 attempts
                    raise Exception("Connection lost")
                await super().send_text(message)
        
        failing_websocket = FailingWebSocket()
        manager = ConnectionManager()
        
        # Connect WebSocket
        await manager.connect(failing_websocket, "1")
        
        # Try to send message - should handle failures gracefully
        await manager.send_processing_update(
            job_id="job_1",
            user_id="1",
            status="processing",
            progress=50,
            message="Test message",
            data={}
        )
        
        # Verify connection was removed from active connections after failure
        # (The failing connection should be cleaned up)
        await asyncio.sleep(0.1)  # Allow cleanup to complete
        
        # Create new working connection
        working_websocket = MockWebSocket()
        await manager.connect(working_websocket, "1")
        
        # Send another message
        await manager.send_processing_update(
            job_id="job_1",
            user_id="1",
            status="processing",
            progress=75,
            message="Recovery test message",
            data={}
        )
        
        # Verify new connection received the message
        assert len(working_websocket.messages) == 1
        assert working_websocket.messages[0]["progress"] == 75