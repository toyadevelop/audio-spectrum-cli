#!/usr/bin/env python3
"""Plot a WAV file's time waveform and windowed FFT spectrum."""

import argparse
import sys
import wave
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
from scipy.io import wavfile


def read_wav(path: Path) -> tuple[int, np.ndarray]:
    try:
        sample_rate, data = wavfile.read(path)
    except FileNotFoundError as exc:
        raise ValueError(f"Input file not found: '{path}'") from exc
    except (OSError, EOFError, ValueError) as exc:
        raise ValueError(f"Could not read '{path}' as a valid WAV file: {exc}") from exc

    if data.size == 0:
        raise ValueError(f"WAV file contains no audio samples: '{path}'")
    if data.ndim not in (1, 2):
        raise ValueError("Only mono and multichannel WAV files are supported.")
    if sample_rate <= 0:
        raise ValueError("WAV file has an invalid sample rate.")

    if np.issubdtype(data.dtype, np.unsignedinteger):
        midpoint = (np.iinfo(data.dtype).max + 1) / 2
        audio = (data.astype(np.float64) - midpoint) / midpoint
    elif np.issubdtype(data.dtype, np.signedinteger):
        scale = max(abs(np.iinfo(data.dtype).min), np.iinfo(data.dtype).max)
        audio = data.astype(np.float64) / scale
    elif np.issubdtype(data.dtype, np.floating):
        audio = data.astype(np.float64)
        if not np.all(np.isfinite(audio)):
            raise ValueError("WAV file contains non-finite audio samples.")
    else:
        raise ValueError(f"Unsupported WAV sample format: {data.dtype}")

    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    return sample_rate, audio


def average_spectrum(audio: np.ndarray, sample_rate: int, n_fft: int) -> tuple[np.ndarray, np.ndarray]:
    window = np.hanning(n_fft)
    window_sum = window.sum()
    hop = max(1, n_fft // 2)
    starts = range(0, max(1, audio.size - n_fft + 1), hop)
    amplitude = np.zeros(n_fft // 2 + 1, dtype=np.float64)
    frame_count = 0

    for start in starts:
        frame = np.zeros(n_fft, dtype=np.float64)
        available = min(n_fft, audio.size - start)
        frame[:available] = audio[start : start + available]
        magnitude = np.abs(np.fft.rfft(frame * window)) / window_sum
        magnitude[1:-1 if n_fft % 2 == 0 else None] *= 2
        amplitude += magnitude
        frame_count += 1

    amplitude /= frame_count
    frequencies = np.fft.rfftfreq(n_fft, d=1 / sample_rate)
    return frequencies, amplitude


def create_plot(
    path: Path, output: Path, sample_rate: int, audio: np.ndarray, n_fft: int
) -> None:
    time = np.arange(audio.size) / sample_rate
    frequencies, amplitude = average_spectrum(audio, sample_rate, n_fft)
    spectrum_db = 20 * np.log10(np.maximum(amplitude, 1e-6))
    visible = (frequencies >= 20) & (frequencies <= 20_000)

    figure, (waveform_axis, spectrum_axis) = plt.subplots(
        2, 1, figsize=(11, 7), constrained_layout=True
    )
    waveform_axis.plot(time, audio, linewidth=0.6)
    waveform_axis.set(
        title=f"Time waveform — {path.name}",
        xlabel="Time [s]",
        ylabel="Amplitude [-1 to 1]",
        ylim=(-1, 1),
    )
    waveform_axis.grid(True, alpha=0.3)

    spectrum_axis.plot(frequencies[visible], spectrum_db[visible], linewidth=0.8)
    spectrum_axis.set_xscale("log")
    spectrum_axis.set_xlim(20, 20_000)
    spectrum_axis.set(
        title=f"Windowed FFT spectrum (n_fft={n_fft})",
        xlabel="Frequency [Hz]",
        ylabel="Amplitude [dBFS]",
    )
    spectrum_axis.set_xticks([20, 50, 100, 200, 500, 1000, 2000, 5000, 10_000, 20_000])
    spectrum_axis.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    spectrum_axis.grid(True, which="both", alpha=0.3)

    try:
        figure.savefig(output, dpi=150)
    except OSError as exc:
        raise ValueError(f"Could not write output image '{output}': {exc}") from exc
    finally:
        plt.close(figure)


def compute_spectrogram(
    audio: np.ndarray, sample_rate: int, n_fft: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    window = np.hanning(n_fft)
    frequencies, times, spectrum = signal.stft(
        audio,
        fs=sample_rate,
        window=window,
        nperseg=n_fft,
        noverlap=n_fft // 2,
        nfft=n_fft,
        boundary="zeros",
        padded=True,
        scaling="spectrum",
    )
    amplitude = np.abs(spectrum)
    amplitude[1:-1 if n_fft % 2 == 0 else None] *= 2
    spectrum_db = 20 * np.log10(np.maximum(amplitude, 1e-12))
    return frequencies, times, spectrum_db


def create_spectrogram_plot(
    path: Path,
    output: Path,
    sample_rate: int,
    audio: np.ndarray,
    n_fft: int,
    db_range: float,
    frequency_scale: str,
) -> None:
    time = np.arange(audio.size) / sample_rate
    frequencies, frame_times, spectrum_db = compute_spectrogram(
        audio, sample_rate, n_fft
    )
    upper_frequency = min(20_000, sample_rate / 2)
    if upper_frequency <= 20:
        raise ValueError(
            "Sample rate must be greater than 40 Hz to display frequencies above 20 Hz."
        )
    visible = (frequencies >= 20) & (frequencies <= upper_frequency)
    peak_db = min(float(np.max(spectrum_db)), 0.0)
    floor_db = peak_db - db_range

    figure, (waveform_axis, spectrogram_axis) = plt.subplots(
        2, 1, figsize=(11, 8), constrained_layout=True
    )
    waveform_axis.plot(time, audio, linewidth=0.6)
    waveform_axis.set(
        title=f"Time waveform — {path.name}",
        xlabel="Time [s]",
        ylabel="Amplitude [-1 to 1]",
        ylim=(-1, 1),
    )
    waveform_axis.grid(True, alpha=0.3)

    image = spectrogram_axis.pcolormesh(
        frame_times,
        frequencies[visible],
        np.maximum(spectrum_db[visible], floor_db),
        shading="auto",
        cmap="magma",
        vmin=floor_db,
        vmax=peak_db,
    )
    spectrogram_axis.set(
        title=f"STFT spectrogram (n_fft={n_fft})",
        xlabel="Time [s]",
        ylabel="Frequency [Hz]",
        ylim=(20, upper_frequency),
    )
    if frequency_scale == "log":
        spectrogram_axis.set_yscale("log")
        spectrogram_axis.set_yticks(
            [
                tick
                for tick in (20, 50, 100, 200, 500, 1000, 2000, 5000, 10_000, 20_000)
                if tick <= upper_frequency
            ]
        )
        spectrogram_axis.get_yaxis().set_major_formatter(
            matplotlib.ticker.ScalarFormatter()
        )
    spectrogram_axis.grid(True, which="both", alpha=0.3)
    colorbar = figure.colorbar(image, ax=spectrogram_axis)
    colorbar.set_label("Amplitude [dBFS]")

    try:
        figure.savefig(output, dpi=150)
    except OSError as exc:
        raise ValueError(f"Could not write output image '{output}': {exc}") from exc
    finally:
        plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a waveform and spectrum or spectrogram plot from a WAV file."
    )
    parser.add_argument("input", type=Path, help="Input WAV file")
    parser.add_argument(
        "--mode",
        choices=("spectrum", "spectrogram"),
        default="spectrum",
        help="Plot mode (default: spectrum)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("result.png"),
        help="Output PNG path (default: result.png)",
    )
    parser.add_argument(
        "--n-fft",
        type=int,
        default=2048,
        help="FFT size and analysis window length (default: 2048)",
    )
    parser.add_argument(
        "--db-range",
        type=float,
        default=80,
        help="Spectrogram dynamic range below its peak in dB (default: 80)",
    )
    parser.add_argument(
        "--frequency-scale",
        choices=("log", "linear"),
        default="log",
        help="Spectrogram frequency axis scale (default: log)",
    )
    args = parser.parse_args()
    if args.n_fft < 3:
        parser.error("--n-fft must be at least 3")
    if not np.isfinite(args.db_range) or args.db_range <= 0:
        parser.error("--db-range must be greater than 0")

    try:
        sample_rate, audio = read_wav(args.input)
        if args.mode == "spectrum":
            create_plot(args.input, args.output, sample_rate, audio, args.n_fft)
        else:
            create_spectrogram_plot(
                args.input,
                args.output,
                sample_rate,
                audio,
                args.n_fft,
                args.db_range,
                args.frequency_scale,
            )
    except ValueError as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"Saved plot to {args.output}")


if __name__ == "__main__":
    main()
