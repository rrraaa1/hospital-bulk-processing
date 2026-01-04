"""
Hospital Bulk Processing System - Main Application
FastAPI application for bulk hospital CSV uploads
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any
import time

from app.models import (
    BulkProcessingResponse,
    BatchStatusResponse,
    ValidationResponse,
    ErrorResponse
)
from app.services.csv_processor import CSVProcessor
from app.services.hospital_client import HospitalAPIClient
from app.services.batch_manager import BatchManager
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Hospital Bulk Processing API",
    description="Bulk processing system for hospital CSV uploads",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
csv_processor = CSVProcessor()
hospital_client = HospitalAPIClient(base_url=settings.HOSPITAL_API_URL)
batch_manager = BatchManager()


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Hospital Bulk Processing API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "bulk_upload": "/hospitals/bulk",
            "batch_status": "/hospitals/batch/{batch_id}/status",
            "batch_results": "/hospitals/batch/{batch_id}/results",
            "validate_csv": "/hospitals/validate"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if Hospital API is reachable
        api_healthy = await hospital_client.health_check()
        return {
            "status": "healthy" if api_healthy else "degraded",
            "hospital_api": "connected" if api_healthy else "disconnected",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        )


@app.post("/hospitals/validate", response_model=ValidationResponse)
async def validate_csv(file: UploadFile = File(...)):
    """
    Validate CSV format without processing

    Args:
        file: CSV file with columns: name, address, phone (optional)

    Returns:
        Validation results with any errors found
    """
    try:
        logger.info(f"Validating CSV file: {file.filename}")

        # Read file content
        content = await file.read()

        # Validate CSV
        validation_result = csv_processor.validate_csv(content)

        logger.info(f"Validation completed. Valid: {validation_result['is_valid']}")
        return validation_result

    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/hospitals/bulk", response_model=BulkProcessingResponse)
async def bulk_create_hospitals(file: UploadFile = File(...)):
    """
    Bulk create hospitals from CSV file

    Processing workflow:
    1. Validate CSV format and content
    2. Generate unique batch ID
    3. Create each hospital via Hospital Directory API
    4. Activate batch once all hospitals are created
    5. Return comprehensive results

    Args:
        file: CSV file with columns: name, address, phone (optional)

    Returns:
        Batch processing results with detailed status
    """
    start_time = time.time()

    try:
        logger.info(f"Starting bulk processing for file: {file.filename}")

        # Check file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only CSV files are accepted."
            )

        # Read file content
        content = await file.read()

        # Validate CSV
        validation_result = csv_processor.validate_csv(content)
        if not validation_result['is_valid']:
            raise HTTPException(
                status_code=400,
                detail=f"CSV validation failed: {', '.join(validation_result['errors'])}"
            )

        # Check hospital limit
        if validation_result['total_rows'] > settings.MAX_HOSPITALS_PER_BATCH:
            raise HTTPException(
                status_code=400,
                detail=f"CSV contains {validation_result['total_rows']} hospitals. "
                       f"Maximum allowed is {settings.MAX_HOSPITALS_PER_BATCH}."
            )

        # Parse hospitals from CSV
        hospitals = csv_processor.parse_csv(content)
        logger.info(f"Parsed {len(hospitals)} hospitals from CSV")

        # Generate batch ID and initialize batch
        batch_id = batch_manager.create_batch(len(hospitals))
        logger.info(f"Created batch {batch_id} with {len(hospitals)} hospitals")

        # Process each hospital
        results = []
        failed_count = 0

        for idx, hospital_data in enumerate(hospitals, start=1):
            try:
                # Create hospital via API
                hospital_response = await hospital_client.create_hospital(
                    name=hospital_data['name'],
                    address=hospital_data['address'],
                    phone=hospital_data.get('phone'),
                    batch_id=batch_id
                )

                results.append({
                    "row": idx,
                    "hospital_id": hospital_response['id'],
                    "name": hospital_data['name'],
                    "status": "created"
                })

                # Update batch progress
                batch_manager.update_progress(batch_id, idx)
                logger.info(f"Created hospital {idx}/{len(hospitals)}: {hospital_data['name']}")

            except Exception as e:
                failed_count += 1
                results.append({
                    "row": idx,
                    "hospital_id": None,
                    "name": hospital_data['name'],
                    "status": "failed",
                    "error": str(e)
                })
                logger.error(f"Failed to create hospital {idx}: {str(e)}")

        # Activate batch if all hospitals were created successfully
        batch_activated = False
        if failed_count == 0:
            try:
                await hospital_client.activate_batch(batch_id)
                batch_activated = True

                # Update status for all results
                for result in results:
                    if result['status'] == 'created':
                        result['status'] = 'created_and_activated'

                logger.info(f"Batch {batch_id} activated successfully")
            except Exception as e:
                logger.error(f"Failed to activate batch {batch_id}: {str(e)}")
                batch_activated = False
        else:
            logger.warning(f"Batch {batch_id} not activated due to {failed_count} failures")

        # Calculate processing time
        processing_time = time.time() - start_time

        # Complete batch processing
        batch_manager.complete_batch(
            batch_id=batch_id,
            results=results,
            processing_time=processing_time,
            batch_activated=batch_activated
        )

        # Prepare response
        response = BulkProcessingResponse(
            batch_id=batch_id,
            total_hospitals=len(hospitals),
            processed_hospitals=len(hospitals) - failed_count,
            failed_hospitals=failed_count,
            processing_time_seconds=round(processing_time, 2),
            batch_activated=batch_activated,
            hospitals=results
        )

        logger.info(
            f"Bulk processing completed. Batch: {batch_id}, "
            f"Processed: {response.processed_hospitals}/{response.total_hospitals}, "
            f"Time: {response.processing_time_seconds}s"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk processing error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during bulk processing: {str(e)}"
        )


@app.get("/hospitals/batch/{batch_id}/status", response_model=BatchStatusResponse)
async def get_batch_status(batch_id: str):
    """
    Get current status of batch processing

    Args:
        batch_id: Unique batch identifier

    Returns:
        Current batch status and progress
    """
    try:
        status = batch_manager.get_batch_status(batch_id)
        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Batch {batch_id} not found"
            )
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving batch status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/hospitals/batch/{batch_id}/results")
async def get_batch_results(batch_id: str):
    """
    Get detailed results for a completed batch

    Args:
        batch_id: Unique batch identifier

    Returns:
        Complete processing results
    """
    try:
        results = batch_manager.get_batch_results(batch_id)
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"Results for batch {batch_id} not found"
            )
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving batch results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
