#!/usr/bin/env python3
"""Smoke-test progressive /v1/audio/speech streaming (TTFB vs full download)."""

from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--key", default="dev-key")
    parser.add_argument(
        "--text",
        default=(
            "The lights in the kitchen are already on. "
            "Shall I dim them for dinner, or leave them as they are?"
        ),
    )
    args = parser.parse_args()

    health = urllib.request.urlopen(f"{args.base}/health", timeout=10)
    print("health:", health.status, health.read().decode())

    body = (
        '{"model":"tts-1","input":'
        + _json_str(args.text)
        + ',"voice":"alloy","response_format":"mp3","speed":1.0}'
    ).encode()
    req = urllib.request.Request(
        f"{args.base}/v1/audio/speech",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {args.key}",
        },
        method="POST",
    )

    t0 = time.perf_counter()
    t_first: float | None = None
    total = 0
    head = b""
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            ctype = resp.headers.get("Content-Type", "")
            print("status:", resp.status, "content-type:", ctype)
            while True:
                chunk = resp.read(2048)
                if not chunk:
                    break
                if t_first is None:
                    t_first = time.perf_counter()
                if len(head) < 16:
                    head += chunk
                total += len(chunk)
    except urllib.error.HTTPError as exc:
        print("HTTP error:", exc.code, exc.read().decode(errors="replace")[:500])
        return 1

    t_done = time.perf_counter()
    if t_first is None:
        print("FAIL: no bytes received")
        return 1

    # MP3 often starts with ID3 or 0xFFEx frame sync
    looks_mp3 = head.startswith(b"ID3") or (len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0)
    looks_wav = head.startswith(b"RIFF")
    print(f"first_bytes_hex: {head[:8].hex()}")
    print(f"ttfb_ms: {(t_first - t0) * 1000:.1f}")
    print(f"total_ms: {(t_done - t0) * 1000:.1f}")
    print(f"bytes: {total}")
    print(f"looks_mp3: {looks_mp3} looks_wav: {looks_wav}")

    if looks_wav:
        print("FAIL: got WAV while expecting MP3 (HA streaming path needs real MP3)")
        return 1
    if not looks_mp3:
        print("WARN: first bytes not clearly MP3; check manually")
    if total < 500:
        print("FAIL: audio too small")
        return 1

    sentence_count = sum(1 for sep in ".!?" if sep in args.text) or 1
    # Multi-sentence: first MP3 sentence should land before later sentences finish.
    if sentence_count >= 2 and (t_first - t0) >= (t_done - t0) * 0.92:
        print(
            "FAIL: TTFB too close to total for multi-sentence input "
            f"({sentence_count} sentences) — progressive streaming not visible"
        )
        return 1
    if sentence_count >= 2:
        saved_ms = (t_done - t_first) * 1000
        print(f"stream_headstart_ms: {saved_ms:.1f} (audio after first sentence)")
    print("PASS")
    return 0


def _json_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


if __name__ == "__main__":
    sys.exit(main())
