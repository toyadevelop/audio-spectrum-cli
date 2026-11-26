#!/usr/bin/env python3
"""Generate a deterministic 48 kHz, 16-bit test WAV file."""

import argparse
import wave
from pathlib import Path

import numpy as np


def generate_test_wav(output: Path) -> None:
    sample_rate = 48_000
    duration = 2.0
    sample_count = int(sample_rate * duration)
    time = np.arange(sample_count) / sample_rate
    rng = np.random.default_rng(0)
    signal = (
        0.55 * np.sin(2 * np.pi * 440 * time)
        + 0.25 * np.sin(2 * np.pi * 1000 * time)
        + 0.002 * rng.normal(size=sample_count)
    )
    pcm = np.round(np.clip(signal, -1.0, 1.0) * 32767).astype("<i2")

    try:
        with wave.open(str(output), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm.tobytes())
    except OSError as exc:
        raise OSError(f"Could not write WAV file '{output}': {exc}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a 2-second WAV with 440 Hz, 1 kHz, and faint noise."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("sample.wav"),
        help="Output WAV path (default: sample.wav)",
    )
    args = parser.parse_args()

    try:
        generate_test_wav(args.output)
    except OSError as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"Generated {args.output}")


if __name__ == "__main__":
    main()
