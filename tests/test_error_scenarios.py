"""
Integration tests for error scenarios
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import io

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_upload_without_file(client):
    """Test bulk upload without file"""
    response = client.post("/hospitals/bulk")
    assert response.status_code == 422  # Validation error


def test_upload_empty_file(client):
    """Test upload with empty file"""
    empty_file = io.BytesIO(b"")
    response = client.post(
        "/hospitals/bulk",
        files={"file": ("empty.csv", empty_file, "text/csv")}
    )
    assert response.status_code == 400


def test_upload_invalid_csv_format(client):
    """Test upload with invalid CSV format"""
    invalid_csv = io.BytesIO(b"not,a,valid\ncsv,file")
    response = client.post(
        "/hospitals/bulk",
        files={"file": ("invalid.csv", invalid_csv, "text/csv")}
    )
    assert response.status_code == 400
    assert "validation failed" in response.json()["detail"].lower()


def test_upload_csv_missing_required_column(client):
    """Test CSV missing required column"""
    csv_content = b"name,phone\nHospital A,555-1234"
    csv_file = io.BytesIO(csv_content)

    response = client.post(
        "/hospitals/bulk",
        files={"file": ("test.csv", csv_file, "text/csv")}
    )
    assert response.status_code == 400
    assert "address" in response.json()["detail"].lower()


def test_upload_csv_with_empty_name(client):
    """Test CSV with empty name field"""
    csv_content = b"name,address,phone\n,123 Main St,555-1234"
    csv_file = io.BytesIO(csv_content)

    response = client.post(
        "/hospitals/bulk",
        files={"file": ("test.csv", csv_file, "text/csv")}
    )
    assert response.status_code == 400
    assert "name" in response.json()["detail"].lower()


def test_upload_csv_with_empty_address(client):
    """Test CSV with empty address field"""
    csv_content = b"name,address,phone\nHospital A,,555-1234"
    csv_file = io.BytesIO(csv_content)

    response = client.post(
        "/hospitals/bulk",
        files={"file": ("test.csv", csv_file, "text/csv")}
    )
    assert response.status_code == 400
    assert "address" in response.json()["detail"].lower()


def test_upload_csv_exceeding_name_limit(client):
    """Test CSV with name exceeding character limit"""
    long_name = "A" * 201
    csv_content = f"name,address\n{long_name},123 Main St".encode()
    csv_file = io.BytesIO(csv_content)

    response = client.post(
        "/hospitals/bulk",
        files={"file": ("test.csv", csv_file, "text/csv")}
    )
    assert response.status_code == 400
    assert "200 characters" in response.json()["detail"].lower()


def test_upload_csv_exceeding_max_hospitals(client):
    """Test CSV exceeding maximum hospital limit"""
    # Create CSV with 21 hospitals (max is 20)
    hospitals = "\n".join([f"Hospital {i},Address {i},555-{i:04d}" for i in range(21)])
    csv_content = f"name,address,phone\n{hospitals}".encode()
    csv_file = io.BytesIO(csv_content)

    response = client.post(
        "/hospitals/bulk",
        files={"file": ("test.csv", csv_file, "text/csv")}
    )
    assert response.status_code == 400
    assert "maximum" in response.json()["detail"].lower()


def test_upload_non_csv_file(client):
    """Test upload with non-CSV file"""
    text_file = io.BytesIO(b"This is not a CSV file")
    response = client.post(
        "/hospitals/bulk",
        files={"file": ("test.txt", text_file, "text/plain")}
    )
    assert response.status_code == 400
    assert "csv" in response.json()["detail"].lower()


def test_upload_corrupted_csv(client):
    """Test upload with corrupted CSV data"""
    corrupted_csv = io.BytesIO(b"\xff\xfe\x00\x00Invalid bytes")
    response = client.post(
        "/hospitals/bulk",
        files={"file": ("corrupted.csv", corrupted_csv, "text/csv")}
    )
    assert response.status_code == 400


@patch('app.services.hospital_client.HospitalAPIClient.create_hospital')
async def test_partial_failure_scenario(mock_create, client):
    """Test scenario where some hospitals fail to create"""
    # First hospital succeeds, second fails, third succeeds
    mock_create.side_effect = [
        {"id": 1, "name": "Hospital A", "active": False},
        Exception("API Error"),
        {"id": 3, "name": "Hospital C", "active": False}
    ]

    csv_content = b"name,address\nHospital A,123 St\nHospital B,456 Ave\nHospital C,789 Rd"
    csv_file = io.BytesIO(csv_content)

    response = client.post(
        "/hospitals/bulk",
        files={"file": ("test.csv", csv_file, "text/csv")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data['total_hospitals'] == 3
    assert data['failed_hospitals'] == 1
    assert data['batch_activated'] is False


def test_batch_status_not_found(client):
    """Test getting status for non-existent batch"""
    response = client.get("/hospitals/batch/non-existent-batch-id/status")
    assert response.status_code == 404


def test_batch_results_not_found(client):
    """Test getting results for non-existent batch"""
    response = client.get("/hospitals/batch/non-existent-batch-id/results")
    assert response.status_code == 404


def test_validate_csv_with_warnings(client):
    """Test CSV validation with warnings for unknown columns"""
    csv_content = b"name,address,unknown_column,extra\nHospital A,123 St,value1,value2"
    csv_file = io.BytesIO(csv_content)

    response = client.post(
        "/hospitals/validate",
        files={"file": ("test.csv", csv_file, "text/csv")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data['is_valid'] is True
    assert len(data['warnings']) > 0


def test_health_check_when_api_unavailable(client):
    """Test health check when Hospital API is unavailable"""
    with patch('app.services.hospital_client.HospitalAPIClient.health_check',
               new_callable=AsyncMock) as mock_health:
        mock_health.return_value = False

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'degraded'


def test_health_check_exception(client):
    """Test health check when exception occurs"""
    with patch('app.services.hospital_client.HospitalAPIClient.health_check',
               new_callable=AsyncMock) as mock_health:
        mock_health.side_effect = Exception("Connection failed")

        response = client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data['status'] == 'unhealthy'


@patch('app.services.hospital_client.HospitalAPIClient.create_hospital')
async def test_all_hospitals_fail(mock_create, client):
    """Test scenario where all hospitals fail to create"""
    mock_create.side_effect = Exception("API Error")

    csv_content = b"name,address\nHospital A,123 St\nHospital B,456 Ave"
    csv_file = io.BytesIO(csv_content)

    response = client.post(
        "/hospitals/bulk",
        files={"file": ("test.csv", csv_file, "text/csv")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data['failed_hospitals'] == 2
    assert data['processed_hospitals'] == 0
    assert data['batch_activated'] is False


@patch('app.services.hospital_client.HospitalAPIClient.create_hospital')
@patch('app.services.hospital_client.HospitalAPIClient.activate_batch')
async def test_batch_activation_fails(mock_activate, mock_create, client):
    """Test scenario where batch activation fails"""
    mock_create.return_value = {"id": 1, "name": "Hospital A", "active": False}
    mock_activate.side_effect = Exception("Activation failed")

    csv_content = b"name,address\nHospital A,123 St"
    csv_file = io.BytesIO(csv_content)

    response = client.post(
        "/hospitals/bulk",
        files={"file": ("test.csv", csv_file, "text/csv")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data['processed_hospitals'] == 1
    assert data['batch_activated'] is False


def test_csv_with_special_characters(client):
    """Test CSV with special characters in data"""
    csv_content = b'name,address\n"Hospital, Inc.",123 Main St\n"St. Mary\'s",456 Oak Ave'
    csv_file = io.BytesIO(csv_content)

    response = client.post(
        "/hospitals/validate",
        files={"file": ("test.csv", csv_file, "text/csv")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data['is_valid'] is True


def test_csv_with_unicode_characters(client):
    """Test CSV with unicode characters"""
    csv_content = "name,address\nHôpital français,123 Rue\nБольница,456 Улица".encode('utf-8')
    csv_file = io.BytesIO(csv_content)

    response = client.post(
        "/hospitals/validate",
        files={"file": ("test.csv", csv_file, "text/csv")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data['is_valid'] is True


def test_concurrent_batch_uploads(client):
    """Test multiple concurrent batch uploads"""
    csv_content = b"name,address\nHospital A,123 St"

    responses = []
    for i in range(3):
        csv_file = io.BytesIO(csv_content)
        with patch('app.services.hospital_client.HospitalAPIClient.create_hospital',
                   new_callable=AsyncMock) as mock_create:
            with patch('app.services.hospital_client.HospitalAPIClient.activate_batch',
                       new_callable=AsyncMock) as mock_activate:
                mock_create.return_value = {"id": i, "name": f"Hospital {i}", "active": False}
                mock_activate.return_value = {"status": "activated"}

                response = client.post(
                    "/hospitals/bulk",
                    files={"file": (f"test{i}.csv", csv_file, "text/csv")}
                )
                responses.append(response)

    # All should succeed with unique batch IDs
    batch_ids = set()
    for response in responses:
        assert response.status_code == 200
        batch_ids.add(response.json()['batch_id'])

    assert len(batch_ids) == 3  # All batch IDs should be unique


def test_csv_with_bom(client):
    """Test CSV with UTF-8 BOM"""
    csv_content = b"\xef\xbb\xbfname,address\nHospital A,123 St"
    csv_file = io.BytesIO(csv_content)

    response = client.post(
        "/hospitals/validate",
        files={"file": ("test.csv", csv_file, "text/csv")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data['is_valid'] is True


def test_api_root_endpoint(client):
    """Test root endpoint returns correct information"""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert 'service' in data
    assert 'version' in data
    assert 'endpoints' in data