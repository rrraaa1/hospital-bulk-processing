"""
Unit tests for hospital API client
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.hospital_client import HospitalAPIClient
import httpx


@pytest.fixture
def client():
    return HospitalAPIClient(base_url="https://test-api.com")


@pytest.mark.asyncio
async def test_health_check_success(client):
    """Test successful health check"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await client.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_health_check_404(client):
    """Test health check with 404 (still considered healthy)"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await client.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_health_check_failure(client):
    """Test failed health check"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        result = await client.health_check()
        assert result is False


@pytest.mark.asyncio
async def test_create_hospital_success(client):
    """Test successful hospital creation"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 123,
            "name": "Test Hospital",
            "address": "123 Test St",
            "phone": "555-1234",
            "creation_batch_id": "batch-123",
            "active": False
        }

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await client.create_hospital(
            name="Test Hospital",
            address="123 Test St",
            phone="555-1234",
            batch_id="batch-123"
        )

        assert result['id'] == 123
        assert result['name'] == "Test Hospital"


@pytest.mark.asyncio
async def test_create_hospital_without_phone(client):
    """Test hospital creation without phone"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 124,
            "name": "Test Hospital",
            "address": "123 Test St",
            "phone": None,
            "creation_batch_id": "batch-123",
            "active": False
        }

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await client.create_hospital(
            name="Test Hospital",
            address="123 Test St",
            phone=None,
            batch_id="batch-123"
        )

        assert result['id'] == 124
        assert result['phone'] is None


@pytest.mark.asyncio
async def test_create_hospital_retry_on_timeout(client):
    """Test retry logic on timeout"""
    with patch('httpx.AsyncClient') as mock_client:
        # First two attempts fail, third succeeds
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 125, "name": "Test"}

        mock_post = AsyncMock(
            side_effect=[
                httpx.TimeoutException("Timeout"),
                httpx.TimeoutException("Timeout"),
                mock_response
            ]
        )

        mock_client.return_value.__aenter__.return_value.post = mock_post

        result = await client.create_hospital(
            name="Test Hospital",
            address="123 Test St",
            phone=None,
            batch_id="batch-123"
        )

        assert result['id'] == 125
        assert mock_post.call_count == 3


@pytest.mark.asyncio
async def test_create_hospital_all_retries_fail(client):
    """Test when all retry attempts fail"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_post = AsyncMock(
            side_effect=httpx.TimeoutException("Timeout")
        )

        mock_client.return_value.__aenter__.return_value.post = mock_post

        with pytest.raises(Exception) as exc_info:
            await client.create_hospital(
                name="Test Hospital",
                address="123 Test St",
                phone=None,
                batch_id="batch-123"
            )

        assert "after 3 attempts" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_hospital_api_error(client):
    """Test API error response"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": "Invalid data"}
        mock_response.text = "Bad Request"

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(Exception) as exc_info:
            await client.create_hospital(
                name="Test Hospital",
                address="123 Test St",
                phone=None,
                batch_id="batch-123"
            )

        assert "400" in str(exc_info.value)


@pytest.mark.asyncio
async def test_activate_batch_success(client):
    """Test successful batch activation"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "activated"}

        mock_client.return_value.__aenter__.return_value.patch = AsyncMock(
            return_value=mock_response
        )

        result = await client.activate_batch("batch-123")

        assert result['status'] == "activated"


@pytest.mark.asyncio
async def test_activate_batch_no_content(client):
    """Test batch activation with 204 No Content"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.json.side_effect = Exception("No content")

        mock_client.return_value.__aenter__.return_value.patch = AsyncMock(
            return_value=mock_response
        )

        result = await client.activate_batch("batch-123")

        assert result['status'] == "activated"


@pytest.mark.asyncio
async def test_activate_batch_failure(client):
    """Test failed batch activation"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.return_value = {"error": "Server error"}

        mock_client.return_value.__aenter__.return_value.patch = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(Exception) as exc_info:
            await client.activate_batch("batch-123")

        assert "Failed to activate" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_batch_hospitals(client):
    """Test getting hospitals in a batch"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 1, "name": "Hospital A"},
            {"id": 2, "name": "Hospital B"}
        ]

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await client.get_batch_hospitals("batch-123")

        assert len(result) == 2
        assert result[0]['name'] == "Hospital A"


@pytest.mark.asyncio
async def test_get_batch_hospitals_not_found(client):
    """Test getting hospitals for non-existent batch"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await client.get_batch_hospitals("batch-123")

        assert result == []


@pytest.mark.asyncio
async def test_delete_batch_success(client):
    """Test successful batch deletion"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client.return_value.__aenter__.return_value.delete = AsyncMock(
            return_value=mock_response
        )

        result = await client.delete_batch("batch-123")

        assert result is True


@pytest.mark.asyncio
async def test_delete_batch_failure(client):
    """Test failed batch deletion"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client.return_value.__aenter__.return_value.delete = AsyncMock(
            return_value=mock_response
        )

        result = await client.delete_batch("batch-123")

        assert result is False


@pytest.mark.asyncio
async def test_network_error_handling(client):
    """Test network error handling"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.NetworkError("Network error")
        )

        with pytest.raises(Exception) as exc_info:
            await client.create_hospital(
                name="Test",
                address="123 St",
                phone=None,
                batch_id="batch-123"
            )

        assert "Network error" in str(exc_info.value)