from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from fastapi.responses import StreamingResponse
import io

from .auth import require_api_key
from .tts import synthesize_speech, VOICE_MODEL, VOICE_CONFIG
from .schemas import SpeakRequest, HealthResponse, HelpResponse


app = FastAPI(title="PiperTTS API", version="1.0.0")


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
            }
        },
        authentication="Requires x-api-key header matching one of the configured API_KEYS",
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
            }
        }
    )


@app.post("/speak", dependencies=[Depends(require_api_key)])
def speak(body: SpeakRequest, response: Response) -> StreamingResponse:
    """
    Convert text to speech using Piper TTS.
    Returns WAV audio file.
    """
    # No-store headers to prevent intermediary caching
    response.headers["Cache-Control"] = "no-store"
    
    try:
        # Synthesize speech
        audio_data = synthesize_speech(
            text=body.text,
            speaker=body.speaker or 0,
            noise_scale=body.noise_scale or 0.667,
            length_scale=body.length_scale or 1.0,
            noise_w=body.noise_w or 0.8
        )
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=speech.wav"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating speech: {str(e)}"
        )
