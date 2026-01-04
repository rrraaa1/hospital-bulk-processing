"""
HTTP client for Hospital Directory API integration
"""

import httpx
import logging
from typing import Optional, Dict, Any
import asyncio

from app.config import settings

logger = logging.getLogger(__name__)


class HospitalAPIClient:
    """Client for interacting with Hospital Directory API"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.timeout = settings.API_TIMEOUT
        self.max_retries = settings.MAX_RETRIES
        self.retry_delay = settings.RETRY_DELAY

    async def health_check(self) -> bool:
        """
        Check if Hospital Directory API is reachable

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/hospitals/")
                return response.status_code in [200, 404]  # 404 is ok if no hospitals exist
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False

    async def create_hospital(
            self,
            name: str,
            address: str,
            phone: Optional[str],
            batch_id: str
    ) -> Dict[str, Any]:
        """
        Create a single hospital via API

        Args:
            name: Hospital name
            address: Hospital address
            phone: Hospital phone (optional)
            batch_id: Batch identifier

        Returns:
            Created hospital data

        Raises:
            Exception if creation fails after retries
        """
        payload = {
            "name": name,
            "address": address,
            "creation_batch_id": batch_id
        }

        if phone:
            payload["phone"] = phone

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/hospitals/",
                        json=payload
                    )

                    if response.status_code == 201 or response.status_code == 200:
                        hospital_data = response.json()
                        logger.debug(f"Created hospital: {name} (ID: {hospital_data.get('id')})")
                        return hospital_data
                    else:
                        error_msg = f"API returned status {response.status_code}"
                        try:
                            error_detail = response.json()
                            error_msg += f": {error_detail}"
                        except:
                            error_msg += f": {response.text}"

                        raise Exception(error_msg)

            except httpx.TimeoutException as e:
                last_exception = f"Request timeout: {str(e)}"
                logger.warning(
                    f"Timeout creating hospital '{name}' (attempt {attempt + 1}/{self.max_retries})"
                )
            except httpx.NetworkError as e:
                last_exception = f"Network error: {str(e)}"
                logger.warning(
                    f"Network error creating hospital '{name}' (attempt {attempt + 1}/{self.max_retries})"
                )
            except Exception as e:
                last_exception = str(e)
                logger.warning(
                    f"Error creating hospital '{name}' (attempt {attempt + 1}/{self.max_retries}): {str(e)}"
                )

            # Wait before retry (except on last attempt)
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        # All retries failed
        error_msg = f"Failed to create hospital '{name}' after {self.max_retries} attempts: {last_exception}"
        logger.error(error_msg)
        raise Exception(error_msg)

    async def activate_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Activate all hospitals in a batch

        Args:
            batch_id: Batch identifier

        Returns:
            Activation response

        Raises:
            Exception if activation fails
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.patch(
                    f"{self.base_url}/hospitals/batch/{batch_id}/activate"
                )

                if response.status_code in [200, 204]:
                    logger.info(f"Successfully activated batch {batch_id}")
                    try:
                        return response.json()
                    except:
                        return {"status": "activated"}
                else:
                    error_msg = f"Failed to activate batch {batch_id}. Status: {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f", Detail: {error_detail}"
                    except:
                        error_msg += f", Response: {response.text}"

                    logger.error(error_msg)
                    raise Exception(error_msg)

        except Exception as e:
            logger.error(f"Error activating batch {batch_id}: {str(e)}")
            raise

    async def get_batch_hospitals(self, batch_id: str) -> list:
        """
        Get all hospitals in a batch

        Args:
            batch_id: Batch identifier

        Returns:
            List of hospitals in the batch
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/hospitals/batch/{batch_id}"
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Could not retrieve batch {batch_id} hospitals")
                    return []

        except Exception as e:
            logger.error(f"Error retrieving batch hospitals: {str(e)}")
            return []

    async def delete_batch(self, batch_id: str) -> bool:
        """
        Delete all hospitals in a batch

        Args:
            batch_id: Batch identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.base_url}/hospitals/batch/{batch_id}"
                )

                if response.status_code in [200, 204]:
                    logger.info(f"Successfully deleted batch {batch_id}")
                    return True
                else:
                    logger.warning(f"Failed to delete batch {batch_id}")
                    return False

        except Exception as e:
            logger.error(f"Error deleting batch: {str(e)}")
            return False