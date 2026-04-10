from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import StreamingResponse
import io

from .auth import require_api_key
from .tts import synthesize_speech, VOICE_MODEL
from .schemas import OpenAISpeechRequest, SpeakRequest, HealthResponse, HelpResponse


app = FastAPI(title="PiperTTS API", version="1.0.0")


def _openai_speed_to_length_scale(speed: float) -> float:
    """OpenAI ``speed`` increases playback speed; Piper ``length_scale`` is inverse."""
    return max(0.25, min(4.0, 1.0 / speed))


def _voice_field_to_speaker(voice: str) -> int:
    if voice.isdigit():
        return int(voice)
    return 0


def _wav_response(audio_data: bytes, response: Response) -> StreamingResponse:
    response.headers["Cache-Control"] = "no-store"
    return StreamingResponse(
        io.BytesIO(audio_data),
        media_type="audio/wav",
        headers={"Content-Disposition": "attachment; filename=speech.wav"},
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        model=VOICE_MODEL,
        voice="edwin"
    )


@app.get("/help", response_model=HelpResponse)
def help_endpoint() -> HelpResponse:
    """Help endpoint with API documentation"""
    return HelpResponse(
        endpoints={
            "/health": {
                "method": "GET",
                "description": "Health check endpoint",
                "auth_required": False
            },
            "/help": {
                "method": "GET",
                "description": "API documentation and usage information",
                "auth_required": False
            },
            "/speak": {
                "method": "POST",
                "description": "Convert text to speech",
                "auth_required": True,
                "parameters": {
                    "text": "Text to convert to speech (required)",
                    "speaker": "Speaker ID (optional, default: 0)",
                    "noise_scale": "Noise scale for variability (optional, default: 0.667)",
                    "length_scale": "Length scale for speed (optional, default: 1.0)",
                    "noise_w": "Noise width (optional, default: 0.8)"
                }
            },
            "/v1/audio/speech": {
                "method": "POST",
                "description": "OpenAI-compatible TTS (for Home Assistant openai_tts custom endpoint)",
                "auth_required": True,
                "parameters": {
                    "input": "Text to speak (required)",
                    "model": "Ignored; any string accepted",
                    "voice": "Ignored unless a numeric string (speaker id for multi-speaker models)",
                    "response_format": "mp3, opus, aac, flac, wav, pcm (response is always WAV)",
                    "speed": "0.25–4.0, mapped to Piper length_scale (default: 1.0)",
                    "instructions": "Ignored (OpenAI-only)"
                }
            }
        },
        authentication=(
            "When API_KEYS is set: use x-api-key or Authorization: Bearer <key>. "
            "When API_KEYS is empty: authentication is disabled (local/dev only)."
        ),
        example_usage={
            "minimal": {
                "method": "POST",
                "url": "http://localhost:8000/speak",
                "headers": {
                    "x-api-key": "your-api-key",
                    "content-type": "application/json"
                },
                "body": {
                    "text": "Hello, world!"
                }
            },
            "full": {
                "method": "POST",
                "url": "http://localhost:8000/speak",
                "headers": {
                    "x-api-key": "your-api-key",
                    "content-type": "application/json"
                },
                "body": {
                    "text": "Hello, world!",
                    "speaker": 0,
                    "noise_scale": 0.667,
                    "length_scale": 1.0,
                    "noise_w": 0.8
                }
            },
            "openai_tts_home_assistant": {
                "method": "POST",
                "url": "http://localhost:8000/v1/audio/speech",
                "headers": {
                    "Authorization": "Bearer your-api-key",
                    "content-type": "application/json"
                },
                "body": {
                    "model": "tts-1",
                    "input": "Hello from Home Assistant",
                    "voice": "alloy",
                    "response_format": "mp3",
                    "speed": 1.0
                }
            }
        }
    )


@app.post("/v1/audio/speech", dependencies=[Depends(require_api_key)])
def openai_audio_speech(body: OpenAISpeechRequest, response: Response) -> StreamingResponse:
    """
    OpenAI-compatible speech endpoint for tools like Home Assistant openai_tts.
    Returns WAV; openai_tts detects WAV and converts as needed.
    """
    try:
        audio_data = synthesize_speech(
            text=body.input,
            speaker=_voice_field_to_speaker(body.voice),
            noise_scale=0.667,
            length_scale=_openai_speed_to_length_scale(body.speed),
            noise_w=0.8,
        )
        return _wav_response(audio_data, response)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating speech: {str(e)}",
        )


@app.post("/speak", dependencies=[Depends(require_api_key)])
def speak(body: SpeakRequest, response: Response) -> StreamingResponse:
    """
    Convert text to speech using Piper TTS.
    Returns WAV audio file.
    """
    try:
        audio_data = synthesize_speech(
            text=body.text,
            speaker=body.speaker or 0,
            noise_scale=body.noise_scale or 0.667,
            length_scale=body.length_scale or 1.0,
            noise_w=body.noise_w or 0.8,
        )
        return _wav_response(audio_data, response)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating speech: {str(e)}"
        )
