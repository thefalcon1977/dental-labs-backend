"""Schemas for DenseNet tissue detection."""

from pydantic import BaseModel, Field


class RegionDetection(BaseModel):
    """One tissue region found on the radiograph."""

    x1: int = Field(..., description="Left edge in original image pixels")
    y1: int = Field(..., description="Top edge in original image pixels")
    x2: int = Field(..., description="Right edge in original image pixels")
    y2: int = Field(..., description="Bottom edge in original image pixels")
    class_name: str = Field(..., description="dentin, enamel, or pulp")
    confidence: float = Field(..., description="Softmax confidence from 0 to 1")


class DetectionResponse(BaseModel):
    """Regions returned by the local DenseNet checkpoint."""

    model: str = Field(..., description="Checkpoint filename used for detection")
    filename: str = Field(..., description="Original uploaded filename")
    content_type: str = Field(..., description="Detected image media type")
    confidence_threshold: float = Field(
        ...,
        description="Minimum confidence used for this scan, from 0 to 1",
    )
    detections: list[RegionDetection] = Field(
        ...,
        description="Tissue regions at or above the confidence threshold",
    )
