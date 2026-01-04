"""
Batch tracking and management service
"""

import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BatchManager:
    """Manages batch processing state and results"""

    def __init__(self):
        # In-memory storage for batch information
        self.batches: Dict[str, Dict[str, Any]] = {}

    def create_batch(self, total_hospitals: int) -> str:
        """
        Create a new batch and return its ID

        Args:
            total_hospitals: Total number of hospitals in batch

        Returns:
            Unique batch ID
        """
        batch_id = str(uuid.uuid4())

        self.batches[batch_id] = {
            'batch_id': batch_id,
            'status': 'processing',
            'total_hospitals': total_hospitals,
            'processed_hospitals': 0,
            'progress_percentage': 0.0,
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'completed_at': None,
            'results': None,
            'processing_time': None,
            'batch_activated': False
        }

        logger.info(f"Created batch {batch_id} with {total_hospitals} hospitals")
        return batch_id

    def update_progress(self, batch_id: str, processed_count: int):
        """
        Update progress for a batch

        Args:
            batch_id: Batch identifier
            processed_count: Number of hospitals processed so far
        """
        if batch_id not in self.batches:
            logger.warning(f"Batch {batch_id} not found for progress update")
            return

        batch = self.batches[batch_id]
        batch['processed_hospitals'] = processed_count

        if batch['total_hospitals'] > 0:
            batch['progress_percentage'] = round(
                (processed_count / batch['total_hospitals']) * 100,
                2
            )

        logger.debug(
            f"Batch {batch_id} progress: {processed_count}/{batch['total_hospitals']} "
            f"({batch['progress_percentage']}%)"
        )

    def complete_batch(
            self,
            batch_id: str,
            results: list,
            processing_time: float,
            batch_activated: bool
    ):
        """
        Mark batch as completed and store results

        Args:
            batch_id: Batch identifier
            results: List of hospital processing results
            processing_time: Total processing time in seconds
            batch_activated: Whether batch was successfully activated
        """
        if batch_id not in self.batches:
            logger.warning(f"Batch {batch_id} not found for completion")
            return

        batch = self.batches[batch_id]
        batch['status'] = 'completed'
        batch['completed_at'] = datetime.utcnow().isoformat() + 'Z'
        batch['results'] = results
        batch['processing_time'] = processing_time
        batch['batch_activated'] = batch_activated
        batch['progress_percentage'] = 100.0

        logger.info(
            f"Batch {batch_id} completed. "
            f"Processed: {batch['processed_hospitals']}/{batch['total_hospitals']}, "
            f"Time: {processing_time}s, Activated: {batch_activated}"
        )

    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a batch

        Args:
            batch_id: Batch identifier

        Returns:
            Batch status information or None if not found
        """
        if batch_id not in self.batches:
            logger.warning(f"Batch {batch_id} not found")
            return None

        batch = self.batches[batch_id]

        return {
            'batch_id': batch['batch_id'],
            'status': batch['status'],
            'total_hospitals': batch['total_hospitals'],
            'processed_hospitals': batch['processed_hospitals'],
            'progress_percentage': batch['progress_percentage'],
            'created_at': batch['created_at'],
            'completed_at': batch['completed_at']
        }

    def get_batch_results(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed results for a completed batch

        Args:
            batch_id: Batch identifier

        Returns:
            Complete batch results or None if not found
        """
        if batch_id not in self.batches:
            logger.warning(f"Batch {batch_id} not found")
            return None

        batch = self.batches[batch_id]

        if batch['status'] != 'completed':
            logger.warning(f"Batch {batch_id} is not yet completed")
            return {
                'batch_id': batch_id,
                'status': batch['status'],
                'message': 'Batch processing is not yet completed'
            }

        failed_hospitals = sum(
            1 for result in batch['results']
            if result.get('status') == 'failed'
        )

        return {
            'batch_id': batch['batch_id'],
            'total_hospitals': batch['total_hospitals'],
            'processed_hospitals': batch['processed_hospitals'],
            'failed_hospitals': failed_hospitals,
            'processing_time_seconds': batch['processing_time'],
            'batch_activated': batch['batch_activated'],
            'created_at': batch['created_at'],
            'completed_at': batch['completed_at'],
            'hospitals': batch['results']
        }

    def cleanup_old_batches(self, max_age_hours: int = 24):
        """
        Remove batches older than specified age

        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        current_time = datetime.utcnow()
        batches_to_remove = []

        for batch_id, batch in self.batches.items():
            created_at = datetime.fromisoformat(batch['created_at'].replace('Z', '+00:00'))
            age_hours = (current_time - created_at).total_seconds() / 3600

            if age_hours > max_age_hours:
                batches_to_remove.append(batch_id)

        for batch_id in batches_to_remove:
            del self.batches[batch_id]
            logger.info(f"Cleaned up old batch {batch_id}")

        if batches_to_remove:
            logger.info(f"Cleaned up {len(batches_to_remove)} old batches")