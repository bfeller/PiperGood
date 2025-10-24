from __future__ import annotations

import io
import os
import wave
from pathlib import Path
from typing import Optional

from piper import PiperVoice


VOICE_MODEL = os.getenv("VOICE_MODEL", "/app/voice/edwin.onnx")
VOICE_CONFIG = os.getenv("VOICE_CONFIG", "/app/voice/edwin.onnx.json")

_piper_voice: Optional[PiperVoice] = None


def get_piper_voice() -> PiperVoice:
    global _piper_voice
    if _piper_voice is None:
        model_path = Path(VOICE_MODEL)
        config_path = Path(VOICE_CONFIG)
        
        if not model_path.exists():
            raise FileNotFoundError(f"Voice model not found: {VOICE_MODEL}")
        if not config_path.exists():
            raise FileNotFoundError(f"Voice config not found: {VOICE_CONFIG}")
        
        _piper_voice = PiperVoice.load(model_path, config_path=config_path, use_cuda=False)
    
    return _piper_voice


def synthesize_speech(
    text: str,
    speaker: int = 0,
    noise_scale: float = 0.667,
    length_scale: float = 1.0,
    noise_w: float = 0.8
) -> bytes:
    """
    Synthesize speech from text using Piper TTS.
    Returns WAV audio data as bytes.
    """
    voice = get_piper_voice()
    
    # Create an in-memory WAV file
    wav_buffer = io.BytesIO()
    
    with wave.open(wav_buffer, "wb") as wav_file:
        # Synthesize audio using synthesize_wav method
        voice.synthesize_wav(text, wav_file)
    
    # Get the WAV data
    wav_buffer.seek(0)
    return wav_buffer.read()
