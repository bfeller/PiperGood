from __future__ import annotations

import io
import os
import wave
from collections.abc import Iterator
from pathlib import Path
from typing import Optional

from piper import PiperVoice
from piper.config import SynthesisConfig


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


def _syn_config(
    speaker: int,
    noise_scale: float,
    length_scale: float,
    noise_w: float,
) -> SynthesisConfig:
    return SynthesisConfig(
        speaker_id=speaker,
        length_scale=length_scale,
        noise_scale=noise_scale,
        noise_w_scale=noise_w,
    )


def synthesize_speech(
    text: str,
    speaker: int = 0,
    noise_scale: float = 0.667,
    length_scale: float = 1.0,
    noise_w: float = 0.8,
) -> bytes:
    """
    Synthesize speech from text using Piper TTS.
    Returns WAV audio data as bytes.
    """
    voice = get_piper_voice()
    syn_config = _syn_config(speaker, noise_scale, length_scale, noise_w)

    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file, syn_config=syn_config)

    wav_buffer.seek(0)
    return wav_buffer.read()


def iter_pcm_chunks(
    text: str,
    speaker: int = 0,
    noise_scale: float = 0.667,
    length_scale: float = 1.0,
    noise_w: float = 0.8,
) -> tuple[int, Iterator[bytes]]:
    """
    Stream mono s16le PCM one Piper sentence chunk at a time.

    Returns ``(sample_rate, iterator_of_pcm_bytes)``.
    """
    voice = get_piper_voice()
    syn_config = _syn_config(speaker, noise_scale, length_scale, noise_w)
    sample_rate = int(voice.config.sample_rate)

    def _gen() -> Iterator[bytes]:
        for audio_chunk in voice.synthesize(text, syn_config=syn_config):
            pcm = audio_chunk.audio_int16_bytes
            if pcm:
                yield pcm

    return sample_rate, _gen()
