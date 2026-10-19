from __future__ import annotations

from collections.abc import Iterator
import io
import logging

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from .audio_encode import (
    STREAMABLE_FORMATS,
    iter_stream_encoded_pcm,
    media_for_format,
    transcode_openai_format,
)
from .auth import maybe_log_api_keys_on_startup, require_api_key
from .schemas import HealthResponse, HelpResponse, OpenAISpeechRequest, SpeakRequest
from .tts import VOICE_MODEL, iter_pcm_chunks, synthesize_speech

logger = logging.getLogger(__name__)

app = FastAPI(title="PiperTTS API", version="1.1.0")


@app.on_event("startup")
def _log_startup_api_keys() -> None:
    maybe_log_api_keys_on_startup()


def _openai_speed_to_length_scale(speed: float) -> float:
    """OpenAI ``speed`` increases playback speed; Piper ``length_scale`` is inverse."""
    return max(0.25, min(4.0, 1.0 / speed))


def _voice_field_to_speaker(voice: str) -> int:
    if voice.isdigit():
        return int(voice)
    return 0


def _audio_response(
    audio_data: bytes,
    response: Response,
    *,
    media_type: str,
    filename: str,
) -> StreamingResponse:
    response.headers["Cache-Control"] = "no-store"
    return StreamingResponse(
        io.BytesIO(audio_data),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _stream_openai_speech(body: OpenAISpeechRequest) -> tuple[Iterator[bytes], str, str]:
    """
    Build a progressive audio byte iterator for OpenAI-compatible speech.

    Streamable formats (mp3/opus/aac/pcm) encode Piper sentence chunks as they
    arrive so Home Assistant can begin playback before the full utterance exists.
    wav/flac keep a one-shot encode (headers need known length / full file).
    """
    speaker = _voice_field_to_speaker(body.voice)
    length_scale = _openai_speed_to_length_scale(body.speed)
    fmt = body.response_format
    media_type, filename = media_for_format(fmt)

    if fmt not in STREAMABLE_FORMATS:
        wav_data = synthesize_speech(
            text=body.input,
            speaker=speaker,
            noise_scale=0.667,
            length_scale=length_scale,
            noise_w=0.8,
        )
        payload, media_type, filename = transcode_openai_format(wav_data, fmt)

        def _once() -> Iterator[bytes]:
            yield payload

        return _once(), media_type, filename

    sample_rate, pcm_iter = iter_pcm_chunks(
        text=body.input,
        speaker=speaker,
        noise_scale=0.667,
        length_scale=length_scale,
        noise_w=0.8,
    )
    encoded = iter_stream_encoded_pcm(pcm_iter, sample_rate=sample_rate, fmt=fmt)
    return encoded, media_type, filename


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse(status="ok", model=VOICE_MODEL, voice="edwin")


@app.get("/help", response_model=HelpResponse)
def help_endpoint() -> HelpResponse:
    """Help endpoint with API documentation"""
    return HelpResponse(
        endpoints={
            "/health": {
                "method": "GET",
                "description": "Health check endpoint",
                "auth_required": False,
            },
            "/help": {
                "method": "GET",
                "description": "API documentation and usage information",
                "auth_required": False,
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
                    "noise_w": "Noise width (optional, default: 0.8)",
                },
            },
            "/v1/audio/speech": {
                "method": "POST",
                "description": (
                    "OpenAI-compatible TTS. mp3/opus/aac/pcm stream progressively "
                    "(sentence chunks via Piper → ffmpeg) for Home Assistant openai_tts."
                ),
                "auth_required": True,
                "parameters": {
                    "input": "Text to speak (required)",
                    "model": "Ignored; any string accepted",
                    "voice": "Ignored unless a numeric string (speaker id for multi-speaker models)",
                    "response_format": "mp3 (default), opus, aac, flac, wav, pcm",
                    "speed": "0.25–4.0, mapped to Piper length_scale (default: 1.0)",
                    "stream_format": "Ignored; audio is always chunk-transfer encoded for streamable formats",
                    "instructions": "Ignored (OpenAI-only)",
                },
            },
        },
        authentication=(
            "When API_KEYS is set: use x-api-key or Authorization: Bearer <key>. "
            "When API_KEYS is empty: authentication is disabled (local/dev only)."
        ),
        example_usage={
            "minimal": {
                "method": "POST",
                "url": "http://localhost:8000/speak",
                "headers": {"x-api-key": "your-api-key", "content-type": "application/json"},
                "body": {"text": "Hello, world!"},
            },
            "openai_tts_streaming": {
                "method": "POST",
                "url": "http://localhost:8000/v1/audio/speech",
                "headers": {
                    "Authorization": "Bearer your-api-key",
                    "content-type": "application/json",
                },
                "body": {
                    "model": "tts-1",
                    "input": "First sentence. Second sentence takes longer.",
                    "voice": "alloy",
                    "response_format": "mp3",
                    "speed": 1.0,
                },
            },
        },
    )


@app.post("/v1/audio/speech", dependencies=[Depends(require_api_key)])
def openai_audio_speech(body: OpenAISpeechRequest, response: Response) -> StreamingResponse:
    """
    OpenAI-compatible speech endpoint for tools like Home Assistant openai_tts.

    For mp3/opus/aac/pcm, audio is produced and flushed as Piper finishes each
    sentence so clients using streamed HTTP reads can start decoding early.
    """
    try:
        byte_iter, media_type, filename = _stream_openai_speech(body)
        response.headers["Cache-Control"] = "no-store"
        # Hint that the body is chunked progressively (HA openai_tts streams the read).
        response.headers["X-Accel-Buffering"] = "no"
        return StreamingResponse(
            byte_iter,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("openai speech failed")
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
        return _audio_response(
            audio_data,
            response,
            media_type="audio/wav",
            filename="speech.wav",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating speech: {str(e)}",
        )
