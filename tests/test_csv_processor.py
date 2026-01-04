"""
Unit tests for CSV processor
"""

import pytest
from app.services.csv_processor import CSVProcessor


@pytest.fixture
def csv_processor():
    return CSVProcessor()


def test_valid_csv(csv_processor):
    """Test validation of valid CSV"""
    csv_content = b"name,address,phone\nGeneral Hospital,123 Main St,555-1234\nCity Hospital,456 Oak Ave,555-5678"

    result = csv_processor.validate_csv(csv_content)

    assert result['is_valid'] is True
    assert result['total_rows'] == 2
    assert len(result['errors']) == 0


def test_valid_csv_without_phone(csv_processor):
    """Test validation of CSV without optional phone field"""
    csv_content = b"name,address\nGeneral Hospital,123 Main St\nCity Hospital,456 Oak Ave"

    result = csv_processor.validate_csv(csv_content)

    assert result['is_valid'] is True
    assert result['total_rows'] == 2


def test_missing_required_column(csv_processor):
    """Test validation fails when required column is missing"""
    csv_content = b"name,phone\nGeneral Hospital,555-1234"

    result = csv_processor.validate_csv(csv_content)

    assert result['is_valid'] is False
    assert any('address' in error.lower() for error in result['errors'])


def test_empty_csv(csv_processor):
    """Test validation of empty CSV"""
    csv_content = b""

    result = csv_processor.validate_csv(csv_content)

    assert result['is_valid'] is False
    assert result['total_rows'] == 0


def test_csv_with_empty_required_field(csv_processor):
    """Test validation fails when required field is empty"""
    csv_content = b"name,address,phone\n,123 Main St,555-1234"

    result = csv_processor.validate_csv(csv_content)

    assert result['is_valid'] is False
    assert any('name' in error.lower() for error in result['errors'])


def test_csv_with_name_too_long(csv_processor):
    """Test validation fails when name exceeds max length"""
    long_name = "A" * 201
    csv_content = f"name,address\n{long_name},123 Main St".encode()

    result = csv_processor.validate_csv(csv_content)

    assert result['is_valid'] is False
    assert any('200 characters' in error for error in result['errors'])


def test_csv_with_bom(csv_processor):
    """Test validation handles BOM correctly"""
    csv_content = b"\xef\xbb\xbfname,address\nGeneral Hospital,123 Main St"

    result = csv_processor.validate_csv(csv_content)

    assert result['is_valid'] is True
    assert result['total_rows'] == 1


def test_parse_valid_csv(csv_processor):
    """Test parsing valid CSV into hospital dictionaries"""
    csv_content = b"name,address,phone\nGeneral Hospital,123 Main St,555-1234\nCity Hospital,456 Oak Ave,"

    hospitals = csv_processor.parse_csv(csv_content)

    assert len(hospitals) == 2
    assert hospitals[0]['name'] == "General Hospital"
    assert hospitals[0]['address'] == "123 Main St"
    assert hospitals[0]['phone'] == "555-1234"
    assert hospitals[1]['name'] == "City Hospital"
    assert 'phone' not in hospitals[1]  # Empty phone should not be included


def test_parse_csv_with_extra_columns(csv_processor):
    """Test parsing CSV with extra columns (should be ignored)"""
    csv_content = b"name,address,phone,extra\nGeneral Hospital,123 Main St,555-1234,ignored"

    hospitals = csv_processor.parse_csv(csv_content)

    assert len(hospitals) == 1
    assert 'extra' not in hospitals[0]


def test_csv_validation_with_warnings(csv_processor):
    """Test that warnings are generated for unknown columns"""
    csv_content = b"name,address,unknown_column\nGeneral Hospital,123 Main St,value"

    result = csv_processor.validate_csv(csv_content)

    assert result['is_valid'] is True
    assert len(result['warnings']) > 0
    assert any('unknown_column' in warning.lower() for warning in result['warnings'])


def test_invalid_encoding(csv_processor):
    """Test handling of invalid file encoding"""
    csv_content = b"\xff\xfeInvalid encoding"

    result = csv_processor.validate_csv(csv_content)

    assert result['is_valid'] is False
    assert any('encoding' in error.lower() for error in result['errors'])