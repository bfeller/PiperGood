from __future__ import annotations

import logging
import shutil
import subprocess
from collections.abc import Iterable, Iterator
from typing import Literal

logger = logging.getLogger(__name__)

OpenAIFormat = Literal["mp3", "opus", "aac", "flac", "wav", "pcm"]

# Formats that can be emitted as HTTP chunks before the full clip exists.
STREAMABLE_FORMATS: frozenset[OpenAIFormat] = frozenset({"mp3", "opus", "aac", "pcm"})

# Output: ffmpeg args before "pipe:1" (input is always WAV on stdin for one-shot).
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

# Raw PCM → encoded format (for progressive streaming).
_STREAM_FFMPEG_ARGS: dict[OpenAIFormat, list[str]] = {
    "mp3": ["-f", "mp3", "-c:a", "libmp3lame", "-b:a", "128k"],
    "opus": ["-f", "opus", "-c:a", "libopus", "-b:a", "64k"],
    "aac": ["-f", "adts", "-c:a", "aac", "-b:a", "128k"],
}


def media_for_format(fmt: OpenAIFormat) -> tuple[str, str]:
    return _MEDIA[fmt]


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


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


def _encode_pcm_chunk(pcm: bytes, *, sample_rate: int, fmt: OpenAIFormat) -> bytes:
    """Encode one mono s16le PCM buffer to a complete mp3/opus/aac blob."""
    if fmt not in _STREAM_FFMPEG_ARGS:
        raise ValueError(f"Format {fmt!r} cannot be streamed progressively")

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is not installed; cannot encode non-WAV formats")

    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "s16le",
        "-ar",
        str(sample_rate),
        "-ac",
        "1",
        "-i",
        "pipe:0",
        *_STREAM_FFMPEG_ARGS[fmt],
        "pipe:1",
    ]
    proc = subprocess.run(
        cmd,
        input=pcm,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        err = proc.stderr.decode(errors="replace") if proc.stderr else ""
        logger.error("ffmpeg chunk encode exited %s: %s", proc.returncode, err)
        raise RuntimeError("Audio encoding failed")
    out = proc.stdout or b""
    if not out:
        raise RuntimeError("Audio encoding produced empty output")
    return out


def iter_stream_encoded_pcm(
    pcm_chunks: Iterable[bytes],
    *,
    sample_rate: int,
    fmt: OpenAIFormat,
) -> Iterator[bytes]:
    """
    Progressively encode mono s16le PCM chunks to ``fmt``.

    Piper yields one PCM chunk per sentence. Each chunk is encoded to a
    complete mp3/opus/aac frame sequence and yielded immediately so HTTP
    clients (Home Assistant openai_tts) can start decoding before later
    sentences finish. Concatenated MPEG frames decode fine under ``-f mp3``.

    For ``pcm``, yields the raw PCM unchanged (no ffmpeg).
    """
    if fmt == "pcm":
        for chunk in pcm_chunks:
            if chunk:
                yield chunk
        return

    if fmt not in _STREAM_FFMPEG_ARGS:
        raise ValueError(f"Format {fmt!r} cannot be streamed progressively")

    for pcm in pcm_chunks:
        if not pcm:
            continue
        yield _encode_pcm_chunk(pcm, sample_rate=sample_rate, fmt=fmt)
