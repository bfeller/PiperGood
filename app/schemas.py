from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


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


class OpenAISpeechRequest(BaseModel):
    """Subset of OpenAI ``POST /v1/audio/speech`` for Home Assistant openai_tts compatibility."""

    model_config = ConfigDict(extra="ignore")

    model: str = Field(default="tts-1", description="Ignored; Piper uses the configured voice model.")
    input: str = Field(..., min_length=1, description="Text to synthesize.")
    voice: str = Field(
        default="alloy",
        description="Ignored unless it is a non-negative integer string (multi-speaker Piper voices).",
    )
    response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] = Field(
        default="mp3",
        description=(
            "Output format. mp3/opus/aac/flac/pcm are produced via ffmpeg from Piper WAV; "
            "wav returns raw WAV (best if the client treats the body as WAV)."
        ),
    )
    speed: float = Field(default=1.0, ge=0.25, le=4.0, description="OpenAI speed; mapped to Piper length_scale.")
    instructions: Optional[str] = Field(
        default=None,
        description="OpenAI-only; ignored for Piper.",
    )
