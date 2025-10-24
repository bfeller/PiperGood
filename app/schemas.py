from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SpeakRequest(BaseModel):
    text: str = Field(..., description="Text to convert to speech")
    speaker: Optional[int] = Field(default=0, description="Speaker ID (default: 0)")
    noise_scale: Optional[float] = Field(default=0.667, description="Noise scale for variability (default: 0.667)")
    length_scale: Optional[float] = Field(default=1.0, description="Length scale for speed (default: 1.0)")
    noise_w: Optional[float] = Field(default=0.8, description="Noise width (default: 0.8)")


class HealthResponse(BaseModel):
    status: str
    model: str
    voice: str


class HelpResponse(BaseModel):
    endpoints: dict
    authentication: str
    example_usage: dict
