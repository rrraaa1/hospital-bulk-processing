"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class HospitalCreate(BaseModel):
    """Model for creating a hospital"""
    name: str = Field(..., min_length=1, max_length=200)
    address: str = Field(..., min_length=1, max_length=500)
    phone: Optional[str] = Field(None, max_length=20)
    creation_batch_id: Optional[str] = None


class HospitalResponse(BaseModel):
    """Model for hospital response from API"""
    id: int
    name: str
    address: str
    phone: Optional[str]
    creation_batch_id: Optional[str]
    active: bool
    created_at: str


class HospitalResult(BaseModel):
    """Model for individual hospital processing result"""
    row: int
    hospital_id: Optional[int]
    name: str
    status: str  # created, created_and_activated, failed
    error: Optional[str] = None


class BulkProcessingResponse(BaseModel):
    """Response model for bulk hospital creation"""
    batch_id: str
    total_hospitals: int
    processed_hospitals: int
    failed_hospitals: int
    processing_time_seconds: float
    batch_activated: bool
    hospitals: List[HospitalResult]


class BatchStatusResponse(BaseModel):
    """Response model for batch status"""
    batch_id: str
    status: str  # processing, completed, failed
    total_hospitals: int
    processed_hospitals: int
    progress_percentage: float
    created_at: str
    completed_at: Optional[str] = None


class ValidationResponse(BaseModel):
    """Response model for CSV validation"""
    is_valid: bool
    total_rows: int
    errors: List[str] = []
    warnings: List[str] = []


class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str
    error: Optional[str] = None
    timestamp: Optional[str] = None