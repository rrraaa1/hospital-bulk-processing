"""
Unit tests for batch manager
"""

import pytest
from app.services.batch_manager import BatchManager
from datetime import datetime


@pytest.fixture
def batch_manager():
    return BatchManager()


def test_create_batch(batch_manager):
    """Test batch creation"""
    batch_id = batch_manager.create_batch(total_hospitals=10)

    assert batch_id is not None
    assert len(batch_id) == 36  # UUID length
    assert batch_id in batch_manager.batches


def test_batch_initial_state(batch_manager):
    """Test initial batch state"""
    batch_id = batch_manager.create_batch(total_hospitals=10)
    batch = batch_manager.batches[batch_id]

    assert batch['status'] == 'processing'
    assert batch['total_hospitals'] == 10
    assert batch['processed_hospitals'] == 0
    assert batch['progress_percentage'] == 0.0
    assert batch['completed_at'] is None
    assert batch['batch_activated'] is False


def test_update_progress(batch_manager):
    """Test progress updates"""
    batch_id = batch_manager.create_batch(total_hospitals=10)

    # Update progress
    batch_manager.update_progress(batch_id, 5)
    batch = batch_manager.batches[batch_id]

    assert batch['processed_hospitals'] == 5
    assert batch['progress_percentage'] == 50.0

    # Update to completion
    batch_manager.update_progress(batch_id, 10)
    batch = batch_manager.batches[batch_id]

    assert batch['processed_hospitals'] == 10
    assert batch['progress_percentage'] == 100.0


def test_complete_batch(batch_manager):
    """Test batch completion"""
    batch_id = batch_manager.create_batch(total_hospitals=5)

    results = [
        {"row": 1, "hospital_id": 101, "name": "Hospital A", "status": "created"},
        {"row": 2, "hospital_id": 102, "name": "Hospital B", "status": "created"}
    ]

    batch_manager.complete_batch(
        batch_id=batch_id,
        results=results,
        processing_time=2.5,
        batch_activated=True
    )

    batch = batch_manager.batches[batch_id]

    assert batch['status'] == 'completed'
    assert batch['completed_at'] is not None
    assert batch['results'] == results
    assert batch['processing_time'] == 2.5
    assert batch['batch_activated'] is True
    assert batch['progress_percentage'] == 100.0


def test_get_batch_status(batch_manager):
    """Test getting batch status"""
    batch_id = batch_manager.create_batch(total_hospitals=10)

    status = batch_manager.get_batch_status(batch_id)

    assert status is not None
    assert status['batch_id'] == batch_id
    assert status['status'] == 'processing'
    assert status['total_hospitals'] == 10
    assert status['processed_hospitals'] == 0
    assert 'created_at' in status


def test_get_batch_status_not_found(batch_manager):
    """Test getting status for non-existent batch"""
    status = batch_manager.get_batch_status('non-existent-id')
    assert status is None


def test_get_batch_results_completed(batch_manager):
    """Test getting results for completed batch"""
    batch_id = batch_manager.create_batch(total_hospitals=2)

    results = [
        {"row": 1, "hospital_id": 101, "name": "Hospital A", "status": "created"}
    ]

    batch_manager.complete_batch(
        batch_id=batch_id,
        results=results,
        processing_time=1.0,
        batch_activated=True
    )

    batch_results = batch_manager.get_batch_results(batch_id)

    assert batch_results is not None
    assert batch_results['batch_id'] == batch_id
    assert batch_results['hospitals'] == results
    assert batch_results['batch_activated'] is True


def test_get_batch_results_not_completed(batch_manager):
    """Test getting results for incomplete batch"""
    batch_id = batch_manager.create_batch(total_hospitals=5)

    results = batch_manager.get_batch_results(batch_id)

    assert results is not None
    assert results['status'] == 'processing'
    assert 'message' in results


def test_get_batch_results_not_found(batch_manager):
    """Test getting results for non-existent batch"""
    results = batch_manager.get_batch_results('non-existent-id')
    assert results is None


def test_multiple_batches(batch_manager):
    """Test managing multiple batches"""
    batch_id1 = batch_manager.create_batch(total_hospitals=5)
    batch_id2 = batch_manager.create_batch(total_hospitals=10)
    batch_id3 = batch_manager.create_batch(total_hospitals=3)

    assert len(batch_manager.batches) == 3
    assert batch_id1 != batch_id2 != batch_id3


def test_batch_with_zero_hospitals(batch_manager):
    """Test batch creation with zero hospitals"""
    batch_id = batch_manager.create_batch(total_hospitals=0)

    batch = batch_manager.batches[batch_id]
    assert batch['total_hospitals'] == 0
    assert batch['progress_percentage'] == 0.0


def test_progress_percentage_calculation(batch_manager):
    """Test progress percentage calculation"""
    batch_id = batch_manager.create_batch(total_hospitals=8)

    # Test various progress points
    test_cases = [
        (2, 25.0),
        (4, 50.0),
        (6, 75.0),
        (8, 100.0)
    ]

    for processed, expected_percentage in test_cases:
        batch_manager.update_progress(batch_id, processed)
        batch = batch_manager.batches[batch_id]
        assert batch['progress_percentage'] == expected_percentage




def test_batch_results_with_failures(batch_manager):
    """Test batch results calculation with failures"""
    batch_id = batch_manager.create_batch(total_hospitals=5)

    results = [
        {"row": 1, "hospital_id": 101, "name": "Hospital A", "status": "created"},
        {"row": 2, "hospital_id": None, "name": "Hospital B", "status": "failed"},
        {"row": 3, "hospital_id": 103, "name": "Hospital C", "status": "created"},
        {"row": 4, "hospital_id": None, "name": "Hospital D", "status": "failed"},
        {"row": 5, "hospital_id": 105, "name": "Hospital E", "status": "created"}
    ]

    batch_manager.complete_batch(
        batch_id=batch_id,
        results=results,
        processing_time=3.0,
        batch_activated=False
    )

    batch_results = batch_manager.get_batch_results(batch_id)

    assert batch_results['failed_hospitals'] == 2
    assert batch_results['batch_activated'] is False