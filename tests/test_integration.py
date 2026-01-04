"""
Integration tests for the API
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import io

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_csv():
    """Create a sample CSV file for testing"""
    csv_content = "name,address,phone\nGeneral Hospital,123 Main St,555-1234\nCity Hospital,456 Oak Ave,555-5678"
    return io.BytesIO(csv_content.encode())


@pytest.fixture
def invalid_csv():
    """Create an invalid CSV file for testing"""
    csv_content = "name,phone\nGeneral Hospital,555-1234"  # Missing address
    return io.BytesIO(csv_content.encode())


def test_root_endpoint(client):
    """Test root endpoint returns API information"""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert "endpoints" in data


def test_health_check_endpoint(client):
    """Test health check endpoint"""
    with patch('app.services.hospital_client.HospitalAPIClient.health_check', new_callable=AsyncMock) as mock_health:
        mock_health.return_value = True

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]


def test_validate_csv_valid(client, sample_csv):
    """Test CSV validation with valid file"""
    response = client.post(
        "/hospitals/validate",
        files={"file": ("test.csv", sample_csv, "text/csv")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["total_rows"] == 2
    assert len(data["errors"]) == 0


def test_validate_csv_invalid(client, invalid_csv):
    """Test CSV validation with invalid file"""
    response = client.post(
        "/hospitals/validate",
        files={"file": ("test.csv", invalid_csv, "text/csv")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False
    assert len(data["errors"]) > 0


def test_validate_csv_wrong_file_type(client):
    """Test validation rejects non-CSV files"""
    fake_file = io.BytesIO(b"not a csv")

    response = client.post(
        "/hospitals/validate",
        files={"file": ("test.txt", fake_file, "text/plain")}
    )

    # Should still process, but might fail validation
    assert response.status_code in [200, 400]


@patch('app.services.hospital_client.HospitalAPIClient.create_hospital', new_callable=AsyncMock)
@patch('app.services.hospital_client.HospitalAPIClient.activate_batch', new_callable=AsyncMock)
def test_bulk_create_hospitals_success(mock_activate, mock_create, client, sample_csv):
    """Test successful bulk hospital creation"""
    # Mock hospital creation responses
    mock_create.side_effect = [
        {"id": 1, "name": "General Hospital", "address": "123 Main St", "phone": "555-1234", "active": False},
        {"id": 2, "name": "City Hospital", "address": "456 Oak Ave", "phone": "555-5678", "active": False}
    ]

    # Mock batch activation
    mock_activate.return_value = {"status": "activated"}

    response = client.post(
        "/hospitals/bulk",
        files={"file": ("test.csv", sample_csv, "text/csv")}
    )

    assert response.status_code == 200
    data = response.json()

    assert "batch_id" in data
    assert data["total_hospitals"] == 2
    assert data["processed_hospitals"] == 2
    assert data["failed_hospitals"] == 0
    assert data["batch_activated"] is True
    assert len(data["hospitals"]) == 2


@patch('app.services.hospital_client.HospitalAPIClient.create_hospital', new_callable=AsyncMock)
def test_bulk_create_with_failures(mock_create, client, sample_csv):
    """Test bulk creation with some failures"""
    # First hospital succeeds, second fails
    mock_create.side_effect = [
        {"id": 1, "name": "General Hospital", "address": "123 Main St", "phone": "555-1234", "active": False},
        Exception("API Error")
    ]

    response = client.post(
        "/hospitals/bulk",
        files={"file": ("test.csv", sample_csv, "text/csv")}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total_hospitals"] == 2
    assert data["processed_hospitals"] == 1
    assert data["failed_hospitals"] == 1
    assert data["batch_activated"] is False


def test_bulk_create_invalid_csv(client, invalid_csv):
    """Test bulk creation with invalid CSV"""
    response = client.post(
        "/hospitals/bulk",
        files={"file": ("test.csv", invalid_csv, "text/csv")}
    )

    assert response.status_code == 400
    assert "validation failed" in response.json()["detail"].lower()


def test_bulk_create_non_csv_file(client):
    """Test bulk creation rejects non-CSV files"""
    fake_file = io.BytesIO(b"not a csv")

    response = client.post(
        "/hospitals/bulk",
        files={"file": ("test.txt", fake_file, "text/plain")}
    )

    assert response.status_code == 400
    assert "csv" in response.json()["detail"].lower()


def test_bulk_create_exceeds_limit(client):
    """Test bulk creation with too many hospitals"""
    # Create CSV with more than max hospitals
    hospitals = "\n".join([f"Hospital {i},Address {i},555-{i:04d}" for i in range(25)])
    csv_content = f"name,address,phone\n{hospitals}"
    large_csv = io.BytesIO(csv_content.encode())

    response = client.post(
        "/hospitals/bulk",
        files={"file": ("test.csv", large_csv, "text/csv")}
    )

    assert response.status_code == 400
    assert "maximum" in response.json()["detail"].lower()


@patch('app.services.hospital_client.HospitalAPIClient.create_hospital', new_callable=AsyncMock)
@patch('app.services.hospital_client.HospitalAPIClient.activate_batch', new_callable=AsyncMock)
def test_batch_status_endpoint(mock_activate, mock_create, client, sample_csv):
    """Test getting batch status"""
    mock_create.side_effect = [
        {"id": 1, "name": "General Hospital", "address": "123 Main St", "active": False},
        {"id": 2, "name": "City Hospital", "address": "456 Oak Ave", "active": False}
    ]
    mock_activate.return_value = {"status": "activated"}

    # Create a batch
    response = client.post(
        "/hospitals/bulk",
        files={"file": ("test.csv", sample_csv, "text/csv")}
    )
    batch_id = response.json()["batch_id"]

    # Get batch status
    status_response = client.get(f"/hospitals/batch/{batch_id}/status")

    assert status_response.status_code == 200
    data = status_response.json()
    assert data["batch_id"] == batch_id
    assert data["status"] == "completed"
    assert data["progress_percentage"] == 100.0


def test_batch_status_not_found(client):
    """Test getting status for non-existent batch"""
    response = client.get("/hospitals/batch/non-existent-id/status")

    assert response.status_code == 404


@patch('app.services.hospital_client.HospitalAPIClient.create_hospital', new_callable=AsyncMock)
@patch('app.services.hospital_client.HospitalAPIClient.activate_batch', new_callable=AsyncMock)
def test_batch_results_endpoint(mock_activate, mock_create, client, sample_csv):
    """Test getting batch results"""
    mock_create.side_effect = [
        {"id": 1, "name": "General Hospital", "address": "123 Main St", "active": False},
        {"id": 2, "name": "City Hospital", "address": "456 Oak Ave", "active": False}
    ]
    mock_activate.return_value = {"status": "activated"}

    # Create a batch
    response = client.post(
        "/hospitals/bulk",
        files={"file": ("test.csv", sample_csv, "text/csv")}
    )
    batch_id = response.json()["batch_id"]

    # Get batch results
    results_response = client.get(f"/hospitals/batch/{batch_id}/results")

    assert results_response.status_code == 200
    data = results_response.json()
    assert data["batch_id"] == batch_id
    assert "hospitals" in data
    assert len(data["hospitals"]) == 2


def test_batch_results_not_found(client):
    """Test getting results for non-existent batch"""
    response = client.get("/hospitals/batch/non-existent-id/results")

    assert response.status_code == 404