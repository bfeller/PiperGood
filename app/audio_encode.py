from __future__ import annotations

import logging
import shutil
import subprocess
from typing import Literal

logger = logging.getLogger(__name__)

OpenAIFormat = Literal["mp3", "opus", "aac", "flac", "wav", "pcm"]

# Output: ffmpeg args before "pipe:1" (input is always WAV on stdin).
_FORMAT_FFMPEG_ARGS: dict[OpenAIFormat, list[str]] = {
    "mp3": ["-f", "mp3", "-c:a", "libmp3lame", "-b:a", "128k"],
    "opus": ["-f", "opus", "-c:a", "libopus", "-b:a", "64k"],
    "aac": ["-f", "adts", "-c:a", "aac", "-b:a", "128k"],
    "flac": ["-f", "flac", "-c:a", "flac"],
    "pcm": ["-f", "s16le", "-c:a", "pcm_s16le"],
    "wav": [],
}

_MEDIA: dict[OpenAIFormat, tuple[str, str]] = {
    "mp3": ("audio/mpeg", "speech.mp3"),
    "opus": ("audio/opus", "speech.opus"),
    "aac": ("audio/aac", "speech.aac"),
    "flac": ("audio/flac", "speech.flac"),
    "wav": ("audio/wav", "speech.wav"),
    "pcm": ("audio/pcm", "speech.pcm"),
}


def transcode_openai_format(wav_bytes: bytes, fmt: OpenAIFormat) -> tuple[bytes, str, str]:
    """
    Transcode Piper WAV bytes to the requested OpenAI-style format.
    Returns (body_bytes, media_type, filename).
    """
    if fmt == "wav":
        return wav_bytes, _MEDIA["wav"][0], _MEDIA["wav"][1]

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is not installed; cannot encode non-WAV formats")

    extra = _FORMAT_FFMPEG_ARGS[fmt]
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "wav",
        "-i",
        "pipe:0",
        *extra,
        "pipe:1",
    ]
    proc = subprocess.run(
        cmd,
        input=wav_bytes,
        capture_output=True,
        timeout=300,
        check=False,
    )
    if proc.returncode != 0:
        err = proc.stderr.decode(errors="replace") if proc.stderr else ""
        logger.error("ffmpeg exited %s: %s", proc.returncode, err)
        raise RuntimeError("Audio encoding failed")

    out = proc.stdout or b""
    if not out:
        raise RuntimeError("Audio encoding produced empty output")

    mt, fn = _MEDIA[fmt]
    return out, mt, fn
